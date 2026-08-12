"""Explicit, idempotent bootstrap for one verified platform administrator."""
import argparse
from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--username",required=True); parser.add_argument("--user-id",required=True,type=int); args=parser.parse_args()
    app=create_app()
    with app.app_context():
        rows=ExpertUser.query.filter((ExpertUser.username==args.username)|(ExpertUser.id==args.user_id)).all()
        if len(rows)!=1 or rows[0].id!=args.user_id or rows[0].username!=args.username or not rows[0].is_active:
            raise SystemExit("Refusing promotion: identity is missing, inactive, or ambiguous.")
        rows[0].authority="PLATFORM_ADMIN"; db.session.commit()
        print(f"user_id={rows[0].id} username={rows[0].username} authority={rows[0].authority}")
if __name__ == "__main__": main()
