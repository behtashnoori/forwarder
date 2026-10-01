"""Persian presentation of the governed catalog; source identities stay intact."""
from sqlalchemy import func

# Errata are keyed by the upstream stable identity, never by a guessed name.
PERSIAN_LABELS = {131222: "هرمزگان", 418862: "اصفهان", 418863: "اصفهان"}
CHARACTERS = {"أ": "ا", "إ": "ا", "آ": "ا", "ي": "ی", "ى": "ی", "ك": "ک", "\u200c": "", " ": ""}


def name_fa(row):
    return PERSIAN_LABELS.get(row.geoname_id, row.name_fa or row.name_en)


def normalize(value):
    for old, new in CHARACTERS.items():
        value = value.replace(old, new)
    return value.casefold()


def searchable(column):
    for old, new in CHARACTERS.items():
        column = func.replace(column, old, new)
    return func.lower(column)


def pattern(value):
    return "%" + normalize(value).replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
