"""Reproduce the worldwide FWD-02 reference input from the official release ZIP.

Offline transformation only; no database, network, translations or geocoding.
Source: UNECE UN/LOCODE 2025-1, CC BY 4.0. Retain the original v1 snapshot.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://opensource.unicc.org/un/unece/uncefact/vocab-locode/-/jobs/artifacts/2025-1/download?job=package-release"
SOURCE_SHA256 = "ad409fc7149b10f98d61190c34d9daf78b78bb8b31464cc66de1a89d09b01b5d"
FUNCTION_TYPES = {"1-------": "port", "---4----": "airport"}
ACCEPTED_STATUSES = frozenset({"AA", "AC", "AF", "AI", "AS", "AM", "AQ", "RN", "RL"})


def build(archive: Path) -> dict:
    raw = archive.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Official release archive checksum mismatch")
    baseline = json.loads((ROOT / "backend/reference_data/international-geography-v1.json").read_text(encoding="utf-8"))
    records = {item["country"]["code"]: item for item in baseline["records"]}
    with zipfile.ZipFile(io.BytesIO(raw)) as source:
        rows = []
        for name in sorted(source.namelist()):
            if name.startswith("release/csv/UNLOCODE CodeListPart"):
                rows.extend(csv.reader(io.StringIO(source.read(name).decode("utf-8-sig"))))
    # All country headings, independent of whether the source has a
    # usable continuation. Catalog existence is not a business service promise.
    for row in rows:
        if len(row) != 12 or row[2] or not row[3].startswith("."):
            continue
        code, name = row[1], row[3][1:]
        if code not in records:
            records[code] = {"country": {
                "code": code, "name_en": name, "name_fa": name,
                "source_organization": "UNECE / ISO",
                "source_reference": SOURCE_URL,
                "source_version": "UN/LOCODE 2025-1 / ISO 3166-1",
            }, "locations": []}
    known = {item["un_locode"] for record in records.values() for item in record["locations"]}
    for row in rows:
        if (len(row) != 12 or row[1] not in records or not row[2]
                or row[0].upper() == "X"
                or row[7] not in ACCEPTED_STATUSES):
            continue
        code = row[1] + row[2]
        if code in known:
            continue  # alternate listing labels are not another identity
        known.add(code)
        records[row[1]]["locations"].append({
            "un_locode": code, "name_en": row[3], "name_fa": row[3],
            "city_type": FUNCTION_TYPES.get(row[6], "city"),
            "is_major_port": False, "is_major_airport": False,
            "source_function": row[6], "source_status": row[7],
            "source_coordinates": row[10] or None,
            "source_subdivision": row[5] or None,
        })
    return {
        **{key: value for key, value in baseline.items() if key != "records"},
        "dataset_id": "forwarder-international-geography-v2-fwd02",
        "source_archive_url": SOURCE_URL, "source_archive_sha256": SOURCE_SHA256,
        "source_license": "UNECE UN/CEFACT CC BY 4.0",
        "selection_policy": "Worldwide: every country heading and every non-deleted unique location with AM/AA/AC/AF/AI/AS/AQ/RN/RL status, regardless of function. Preserve every v1 record. Exclude X and unrecognized, unverified or pending statuses. RN is a credible national request and RL confirms existence, not trade suitability. No all-settlements or service-availability claim.",
        "location_defaults": {"source_organization": "UNECE", "source_reference": SOURCE_URL, "source_version": "UN/LOCODE 2025-1"},
        "type_policy": "Preserve v1 types. Single maritime/air functions project to existing port/airport categories; all other or multiple functions project to generic locality (legacy city). This describes a locality, never an exact facility, terminal, municipality or major status.",
        "label_policy": "Preserve v1 Persian labels; new name_fa uses original source name as an explicit untranslated fallback. No inferred translation, city/terminal mapping or major-facility claim.",
        "coordinate_policy": "Source minute-resolution coordinates are evidence only, not a precise facility position and not imported into a runtime coordinate field.",
        "records": [records[code] for code in sorted(records)],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = build(args.archive)
    # One readable record per line; inherited provenance avoids 100k URL copies.
    header = {key: value for key, value in data.items() if key != "records"}
    lines = [json.dumps(header, ensure_ascii=False)[:-1] + ', "records": [']
    for index, record in enumerate(data["records"]):
        lines.append('{"country": ' + json.dumps(record["country"], ensure_ascii=False) + ', "locations": [')
        lines.extend(json.dumps(item, ensure_ascii=False) + ("," if i < len(record["locations"]) - 1 else "") for i, item in enumerate(record["locations"]))
        lines.append("]}" + ("," if index < len(data["records"]) - 1 else ""))
    lines.append("]}")
    args.output.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
