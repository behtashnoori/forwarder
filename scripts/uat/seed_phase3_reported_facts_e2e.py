"""Owned P3-07 browser fixture extends the real P3-05 shipment and units."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.extensions import db
from backend.operational_models import RouteStageExecution
from scripts.uat.seed_phase3_cargo_allocation_e2e import main as seed_cargo


def main():
    seed_cargo()
    path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture = json.loads(path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)
    with app.app_context():
        fixture["p307_units"] = [RouteStageExecution.query.filter_by(public_id=fixture[key]).one().execution_unit.public_id
                                 for key in ("p305_first", "p305_second")]
        db.session.remove()
    path.write_text(json.dumps(fixture), encoding="utf-8")


if __name__ == "__main__": main()
