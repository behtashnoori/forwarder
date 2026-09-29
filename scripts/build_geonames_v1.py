"""Build the governed GeoNames Admin1/city package outside Product state.

Sources are official GeoNames daily downloadable extracts. The output is
deterministic for identical source bytes and includes source checksums, processing
rules, qualification results, and the qualified records. It performs no database
writes.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
from datetime import datetime, timezone
import urllib.request
import zipfile


COUNTRIES = ("IR", "CN", "KZ", "TM", "UZ", "KG", "TJ", "AF", "PK", "AZ", "AM", "GE", "TR", "RU")
BASE_URL = "https://download.geonames.org/export/dump"
DATASET_ID = "GEONAMES_ADMIN1_CITY_V1"
CITY_FEATURES = frozenset({"PPL", "PPLA", "PPLA2", "PPLA3", "PPLA4", "PPLC", "PPLG", "PPLL", "PPLR", "PPLS"})
PRESENCE = {
    "IR": ("تهران", "اصفهان", "بندرعباس", "تبریز", "مشهد", "شیراز", "کرمان", "یزد", "اهواز", "رشت"),
    "CN": ("Shanghai", "Shenzhen", "Guangzhou", "Ningbo", "Qingdao", "Tianjin", "Beijing", "Zhengzhou", "Xi'an", "Wuhan", "Chengdu", "Chongqing", "Yiwu", "Urumqi", "Kashgar", "Horgos"),
    "CORRIDOR": ("Almaty", "Astana", "Aktau", "Ashgabat", "Turkmenabat", "Mary", "Tashkent", "Samarkand", "Bukhara", "Bishkek", "Osh", "Dushanbe", "Baku", "Yerevan", "Istanbul", "Ankara", "Van", "Karachi", "Quetta", "Kabul", "Herat", "Moscow", "Astrakhan"),
}


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def download(url: str, cache: Path) -> bytes:
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / url.rsplit("/", 1)[-1]
    if target.exists():
        return target.read_bytes()
    request = urllib.request.Request(url, headers={"User-Agent": "Forwarder governed-reference-builder/1"})
    with urllib.request.urlopen(request, timeout=180) as response:
        value = response.read()
    target.write_bytes(value)
    return value


def source_record(url: str, blob: bytes, cache: Path) -> dict:
    target = cache / url.rsplit("/", 1)[-1]
    retrieved = datetime.fromtimestamp(target.stat().st_mtime, tz=timezone.utc).isoformat()
    return {"url": url, "file": target.name, "sha256": sha256(blob), "bytes": len(blob), "downloaded_at": retrieved}


def geoname_rows(blob: bytes, member: str):
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        with archive.open(member) as source:
            for raw in source:
                columns = raw.decode("utf-8").rstrip("\n").split("\t")
                if len(columns) != 19:
                    raise ValueError(f"invalid GeoNames row in {member}")
                yield columns


def aliases(columns: list[str]) -> list[str]:
    values = [columns[1], columns[2], *columns[3].split(",")]
    return sorted({value.strip() for value in values if value.strip()}, key=lambda value: (value.casefold(), value))


def preferred_name(values: list[str], fallback: str, language: str) -> str:
    if language == "fa":
        localized = [value for value in values if any("\u0600" <= char <= "\u06ff" for char in value)]
        if localized:
            return min(localized, key=lambda value: (len(value), value))
    return fallback


def build(cache: Path) -> dict:
    sources = []
    country_blobs: dict[str, bytes] = {}
    for code in COUNTRIES:
        url = f"{BASE_URL}/{code}.zip"
        blob = download(url, cache)
        sources.append(source_record(url, blob, cache))
        country_blobs[code] = blob
    cities_url = f"{BASE_URL}/cities500.zip"
    cities_blob = download(cities_url, cache)
    sources.append(source_record(cities_url, cities_blob, cache))

    admin1: list[dict] = []
    admin_key: dict[tuple[str, str], int] = {}
    for code, blob in country_blobs.items():
        for row in geoname_rows(blob, f"{code}.txt"):
            if row[6] != "A" or row[7] != "ADM1" or row[8] != code or not row[10] or row[10] == "00":
                continue
            names = aliases(row)
            item = {
                "geoname_id": int(row[0]), "country_code": code, "admin1_code": row[10],
                "name": row[1], "name_ascii": row[2] or row[1],
                "name_fa": preferred_name(names, row[1], "fa"), "aliases": names,
                "latitude": row[4], "longitude": row[5], "timezone": row[17],
            }
            key = (code, row[10])
            if key in admin_key:
                raise ValueError(f"duplicate Admin1 key {key}")
            admin_key[key] = item["geoname_id"]
            admin1.append(item)

    cities: list[dict] = []
    seen: set[int] = set()
    excluded_unparented: list[int] = []
    for row in geoname_rows(cities_blob, "cities500.txt"):
        if row[8] not in COUNTRIES or row[6] != "P" or row[7] not in CITY_FEATURES:
            continue
        identity = int(row[0])
        if identity in seen:
            raise ValueError(f"duplicate city identity {identity}")
        seen.add(identity)
        parent = admin_key.get((row[8], row[10]))
        if parent is None:
            excluded_unparented.append(identity)
            continue
        names = aliases(row)
        cities.append({
            "geoname_id": identity, "admin1_geoname_id": parent, "country_code": row[8],
            "feature_code": row[7], "name": row[1], "name_ascii": row[2] or row[1],
            "name_fa": preferred_name(names, row[1], "fa"), "aliases": names,
            "latitude": row[4], "longitude": row[5], "population": int(row[14] or 0),
            "timezone": row[17],
        })

    searchable = {}
    for city in cities:
        for value in city["aliases"]:
            searchable.setdefault(value.casefold(), set()).add(city["country_code"])
    presence = {}
    for scope, names in PRESENCE.items():
        presence[scope] = {name: bool(searchable.get(name.casefold())) for name in names}
    missing = [f"{scope}:{name}" for scope, checks in presence.items() for name, found in checks.items() if not found]
    invalid_coordinates = [item["geoname_id"] for item in [*admin1, *cities]
                           if not item["latitude"] or not item["longitude"]]
    invalid_aliases = [item["geoname_id"] for item in [*admin1, *cities] if not item["aliases"]]
    if missing or invalid_coordinates or invalid_aliases:
        raise ValueError(
            "qualification failed: "
            f"missing={missing} coordinates={len(invalid_coordinates)} aliases={len(invalid_aliases)}"
        )
    admin1.sort(key=lambda item: (item["country_code"], item["admin1_code"], item["geoname_id"]))
    cities.sort(key=lambda item: (item["country_code"], item["admin1_geoname_id"], item["name_ascii"].casefold(), item["geoname_id"]))
    return {
        "dataset_id": DATASET_ID,
        "license": {"name": "Creative Commons Attribution 4.0", "url": "https://creativecommons.org/licenses/by/4.0/", "attribution": "GeoNames"},
        "source_family": "GeoNames official downloadable daily extracts",
        "source_readme": f"{BASE_URL}/readme.txt",
        "sources": sources,
        "processing_rules": {
            "countries": list(COUNTRIES), "country_catalog_action": "reuse existing ISO catalog; never create countries",
            "admin1": "country extracts; feature_class=A and feature_code=ADM1; exclude admin1 code 00",
            "cities": "cities500; selected countries; feature_class=P; approved populated-place feature codes; require a resolvable non-00 Admin1 parent",
            "aliases": "GeoNames name, asciiname, and embedded alternate names; normalized only at search time",
            "legacy_matching": "none; apply by stable geoname_id only",
        },
        "qualification": {
            "passed": True, "admin1_count": len(admin1), "city_count": len(cities),
            "duplicate_admin1_identities": 0, "duplicate_city_identities": 0,
            "orphan_city_count": 0, "excluded_unparented_source_count": len(excluded_unparented),
            "invalid_coordinate_count": 0, "invalid_alias_count": 0, "presence": presence,
        },
        "admin1": admin1,
        "cities": cities,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build(args.cache)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as target:
        with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as compressed:
            compressed.write(raw)
    print(json.dumps({"output": str(args.output), "sha256": sha256(args.output.read_bytes()), **payload["qualification"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
