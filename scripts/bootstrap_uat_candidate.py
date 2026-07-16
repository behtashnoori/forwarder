"""Controlled reference-only UAT bootstrap (dry-run by default)."""
from __future__ import annotations
import argparse, os
from pathlib import Path
from urllib.parse import urlsplit
import psycopg2

SOURCE_DB = "forwarder_db"
SOURCE_REVISION = "54ea21ea0d9f"
TARGET_PREFIX = "forwarder_candidate_uat_"
TARGET_REVISION = "20260717_add_customs_office_domain"
EXPECTED = {"province": 31, "county": 425, "city": 425, "iran_port": 12, "port_province_mapping": 372}


def _url(value): return value.replace("postgresql+psycopg2://", "postgresql://", 1)
def _dbname(url): return urlsplit(_url(url)).path.lstrip("/")
def _read_source_url():
    value = os.environ.get("SOURCE_DATABASE_URL")
    if value: return value
    for line in Path(".env").read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("DATABASE_URL="): return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("source URL is missing")


def inspect(source_url, target_url):
    if _dbname(source_url) != SOURCE_DB: raise RuntimeError("source must be forwarder_db")
    if not _dbname(target_url).startswith(TARGET_PREFIX) or _dbname(target_url) == SOURCE_DB: raise RuntimeError("unsafe target database name")
    source = psycopg2.connect(_url(source_url)); target = psycopg2.connect(_url(target_url))
    try:
        source.set_session(readonly=True, autocommit=False); sc = source.cursor(); sc.execute("BEGIN TRANSACTION READ ONLY"); sc.execute("SHOW transaction_read_only")
        if sc.fetchone()[0] != "on": raise RuntimeError("source session is not read-only")
        sc.execute("select version_num from alembic_version"); source_revision = sc.fetchone()[0]
        tc = target.cursor(); tc.execute("select version_num from alembic_version"); target_revision = tc.fetchone()[0]
        if source_revision != SOURCE_REVISION or target_revision != TARGET_REVISION: raise RuntimeError("unexpected source or target revision")
        counts = {}
        for table in EXPECTED:
            sc.execute(f"select count(*) from {table}"); counts[table] = sc.fetchone()[0]
        if counts != EXPECTED: raise RuntimeError(f"unexpected source reference counts: {counts}")
        for table in ("shipment_request", "customer", "expert_user"):
            tc.execute(f"select count(*) from {table}")
            if tc.fetchone()[0] != 0: raise RuntimeError(f"target table is not empty: {table}")
        target_counts = {}
        for table in EXPECTED:
            tc.execute(f"select count(*) from {table}"); target_counts[table] = tc.fetchone()[0]
        tc.execute("select count(*) from country where code='IR'"); target_ir = tc.fetchone()[0]
        if not (all(v == 0 for v in target_counts.values()) and target_ir == 0) and not (target_counts == EXPECTED and target_ir == 1):
            raise RuntimeError(f"target reference state is partial: {target_counts}, IR={target_ir}")
        source.rollback(); target.rollback(); return counts
    finally: source.close(); target.close()


def apply(source_url, target_url):
    inspect(source_url, target_url)
    source = psycopg2.connect(_url(source_url)); target = psycopg2.connect(_url(target_url))
    try:
        source.set_session(readonly=True, autocommit=False); sc=source.cursor(); sc.execute("BEGIN TRANSACTION READ ONLY")
        tc=target.cursor(); tc.execute("select count(*) from province")
        if tc.fetchone()[0] != 0: raise RuntimeError("apply requires an empty target reference state")
        tc.execute("insert into country(name_en,name_fa,code,is_active,created_at) values (%s,%s,%s,true,now())", ("Iran","ایران","IR"))
        sc.execute("select code,name_fa from province order by code,name_fa")
        for code,name in sc.fetchall(): tc.execute("insert into province(code,name_fa) values (%s,%s)",(code,name))
        sc.execute("select p.name_fa,c.name_fa from county c join province p on p.id=c.province_id order by p.name_fa,c.name_fa")
        for pname,name in sc.fetchall(): tc.execute("insert into county(name_fa,province_id) select %s,id from province where name_fa=%s",(name,pname))
        sc.execute("select p.name_fa,co.name_fa,ci.name_fa from city ci join county co on co.id=ci.county_id join province p on p.id=ci.province_id order by p.name_fa,co.name_fa,ci.name_fa")
        for pname,cname,name in sc.fetchall(): tc.execute("insert into city(name_fa,county_id,province_id) select %s,co.id,p.id from county co join province p on p.id=co.province_id where p.name_fa=%s and co.name_fa=%s",(name,pname,cname))
        sc.execute("select ip.name_fa,ip.name_en,ip.port_type,p.name_fa,ip.is_major_port,ip.is_active,ip.description from iran_port ip join province p on p.id=ip.province_id order by ip.name_en")
        for fa,en,kind,pname,major,active,desc in sc.fetchall(): tc.execute("insert into iran_port(name_fa,name_en,port_type,province_id,is_major_port,is_active,description,created_at) select %s,%s,%s,id,%s,%s,%s,now() from province where name_fa=%s",(fa,en,kind,major,active,desc,pname))
        sc.execute("select ip.name_en,p.name_fa,m.suitability_score,m.transport_method,m.estimated_days,m.is_recommended from port_province_mapping m join iran_port ip on ip.id=m.port_id join province p on p.id=m.province_id order by ip.name_en,p.name_fa")
        for port,pname,score,method,days,recommended in sc.fetchall(): tc.execute("insert into port_province_mapping(port_id,province_id,suitability_score,transport_method,estimated_days,is_recommended,created_at) select ip.id,p.id,%s,%s,%s,%s,now() from iran_port ip cross join province p where ip.name_en=%s and p.name_fa=%s",(score,method,days,recommended,port,pname))
        for table, expected in EXPECTED.items():
            tc.execute(f"select count(*) from {table}")
            actual=tc.fetchone()[0]
            if actual != expected: raise RuntimeError(f"target {table} count {actual}, expected {expected}")
        tc.execute("select count(*) from country where code='IR'");
        if tc.fetchone()[0] != 1: raise RuntimeError("Iran invariant failed")
        target.commit(); source.rollback()
    except Exception: target.rollback(); source.rollback(); raise
    finally: source.close(); target.close()


def main():
    p=argparse.ArgumentParser(); p.add_argument("--inspect",action="store_true"); p.add_argument("--apply",action="store_true"); p.add_argument("--target-url",default=os.environ.get("TARGET_DATABASE_URL")); args=p.parse_args()
    if not args.target_url: raise SystemExit("TARGET_DATABASE_URL or --target-url is required")
    source=_read_source_url(); counts=inspect(source,args.target_url); print("PLAN="+str(counts)); print("CUSTOMS_REFERENCE_DATA_PENDING")
    if args.apply: apply(source,args.target_url); print("APPLY=completed")
    else: print("DRY_RUN=yes")

if __name__ == "__main__": main()
