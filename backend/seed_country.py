"""Idempotent canonical country seed. This module never writes geography."""
from backend.extensions import db
from backend.models import Country

IRAN = {"code": "IR", "name_en": "Iran", "name_fa": "ایران"}


class CountrySeedConflict(RuntimeError):
    pass


def seed_canonical_iran() -> Country:
    by_code = Country.query.filter(db.func.upper(Country.code) == "IR").all()
    aliases = Country.query.filter(
        db.or_(db.func.lower(Country.name_en).in_(("iran", "islamic republic of iran")),
               Country.name_fa.in_(("ایران", "جمهوری اسلامی ایران")))
    ).all()
    candidates = {row.id: row for row in by_code + aliases}
    if len(candidates) > 1 or (aliases and not by_code):
        raise CountrySeedConflict("conflicting Iran country records")
    if by_code:
        iran = by_code[0]
        if iran.name_en.lower() not in ("iran", "islamic republic of iran") or iran.name_fa not in ("ایران", "جمهوری اسلامی ایران"):
            raise CountrySeedConflict("IR code belongs to an incompatible country record")
        iran.is_active = True
    else:
        iran = Country(**IRAN, is_active=True)
        db.session.add(iran)
    db.session.commit()
    return iran
