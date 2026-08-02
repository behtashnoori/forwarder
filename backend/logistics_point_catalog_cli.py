"""Explicit plan/apply CLI for the LogisticsPointType catalog."""
import argparse,json,sys
from backend import create_app
from backend.config import is_production_environment
from backend.logistics_point_catalog import LogisticsCatalogError,apply_catalog,load_catalog,plan_catalog
from backend.models import ExpertUser

def main(argv=None,*,app=None):
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest="command",required=True);sub.add_parser("plan");apply=sub.add_parser("apply")
    for flag in ("operator","approval-reference","expected-checksum","user-id"):apply.add_argument("--"+flag,required=True)
    apply.add_argument("--confirm",action="store_true");apply.add_argument("--confirm-production",action="store_true");args=parser.parse_args(argv)
    payload=load_catalog();app=app or create_app(skip_startup=True);environment=str(app.config.get("APP_ENV","development")).lower()
    with app.app_context():
        if args.command=="plan":print(json.dumps(plan_catalog(payload,environment),ensure_ascii=False,sort_keys=True));return 0
        if not args.confirm:return 2
        if is_production_environment(environment) and not args.confirm_production:return 2
        try:user_id=int(args.user_id)
        except ValueError:return 2
        if ExpertUser.query.filter_by(id=user_id,is_active=True).one_or_none() is None:return 2
        plan,run=apply_catalog(payload,environment=environment,operator=args.operator,approval_reference=args.approval_reference,expected_checksum=args.expected_checksum,user_id=user_id)
        print(json.dumps({**plan,"run_id":run.public_id,"status":run.status},ensure_ascii=False,sort_keys=True));return 3 if run.status=="refused" else 0
def run(argv=None):
    try:return main(argv)
    except LogisticsCatalogError as exc:print(f"Logistics catalog command failed: {exc}",file=sys.stderr);return 1
    except Exception as exc:print(f"Logistics catalog command failed ({type(exc).__name__}).",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(run())
