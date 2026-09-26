"""Create a true restricted LOGIN only in an explicitly owned loopback test DB."""
import os
import re
import sqlalchemy as sa
from sqlalchemy.engine import make_url


def main():
    raw=os.environ["E2E_DATABASE_URL"]
    url=make_url(raw)
    if url.host not in {"localhost","127.0.0.1"} or not url.database.startswith("forwarder_integrated_cert_p3_06_documents_p313_"):
        raise RuntimeError("P313 runtime provisioning requires its owned synthetic browser database")
    role="p313_browser_"+url.database.rsplit("_",1)[-1]
    if not re.fullmatch(r"p313_browser_[a-f0-9]{8}",role):raise RuntimeError("Invalid owned role identity")
    engine=sa.create_engine(raw)
    with engine.begin() as connection:
        connection.execute(sa.text(f"CREATE ROLE {role} LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"))
        connection.execute(sa.text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        connection.execute(sa.text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {role}"))
        connection.execute(sa.text(f"GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO {role}"))
        connection.execute(sa.text(f"GRANT forwarder_owner_transfer_caller TO {role}"))
    engine.dispose()
    runtime=url.set(username=role,password=None)
    engine=sa.create_engine(runtime)
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT current_user=session_user AND NOT (SELECT rolsuper FROM pg_roles WHERE rolname=current_user)")).scalar()
        assert connection.execute(sa.text("SELECT has_function_privilege(current_user,'public.transfer_shipment_owner(bigint,bigint,bigint,bigint,bigint,integer,text,text,bigint,jsonb)','EXECUTE')")).scalar()
        assert not connection.execute(sa.text("SELECT pg_has_role(current_user,'forwarder_owner_transfer_owner','MEMBER')")).scalar()
    engine.dispose()
    print(runtime.render_as_string(hide_password=False))


if __name__=="__main__": main()
