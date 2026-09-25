"""Exact-Product supplemental A partial-delivery / B actively-in-transit proof."""
import json
import subprocess
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone

root = Path.cwd()
sys.path.insert(0, str(root))
product = '48fa69b70af1bcf06fc5a9783b98fdf54de7a18c'
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip() == product
assert not subprocess.check_output(['git','status','--porcelain'])
from backend.extensions import db
from backend.cargo_models import ShipmentCargoItem, ExecutionUnitCargoAllocation
from backend.operational_models import OperationalShipment, OperationalWorkItem, RouteCargoDestination, RouteStageExecution
from backend.services import cargo_allocation_service as allocation, delivery_service as delivery
from backend.tests.test_operational_vertical_slice import operational_app, _user
from backend.tests.test_phase3_cargo_delivery import setup, payload, record

fixture = operational_app.__wrapped__()
app = next(fixture)
assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'
with app.app_context():
    ctx = setup(app)
    b = ShipmentCargoItem.query.filter_by(public_id=ctx['cargo_b']).one()
    b_stage = RouteStageExecution.query.filter_by(public_id=ctx['second']).one()
    terminal = RouteStageExecution.query.filter_by(public_id=ctx['third']).one()
    db.session.add(RouteCargoDestination(route_plan_id=ctx['plan'], operational_shipment_id=ctx['shipment_id'],
        shipment_cargo_item_id=b.id, destination_route_leg_id=terminal.route_leg_id,
        created_by_user_id=app.config['phase1a']['user']))
    # Explicit synthetic initial state; it is not inferred from missing deliveries.
    b_stage.execution_unit.lifecycle_status = 'in_progress'
    db.session.commit()
    for cargo, stage, amount in ((ctx['cargo'], ctx['first'], '100'),(ctx['cargo_b'],ctx['second'],'25')):
        allocation.set_allocation(ctx['shipment'], cargo, stage,
            {'dimension':'ACTUAL','quantity':amount,'expected_version':0}, _user(app), 'transit-'+cargo)
        db.session.commit()
    shipment = db.session.get(OperationalShipment,ctx['shipment_id'])
    b_allocation = ExecutionUnitCargoAllocation.query.filter_by(shipment_cargo_item_id=b.id,dimension='ACTUAL',is_current=True).one()
    before = (b.quantity,b.planned_quantity,b.actual_quantity,b.version,
        b_allocation.allocated_quantity,b_allocation.version,b_stage.execution_unit.lifecycle_status,
        b_stage.execution_unit.version,shipment.lifecycle_status,shipment.version,OperationalWorkItem.query.count())
    first,_ = record(app,ctx)
    record(app,ctx,payload(ctx,quantity='35'))
    rows=delivery.listing(ctx['shipment'],_user(app))['cargo']
    assert Decimal(rows[0]['delivered'])==95 and Decimal(rows[0]['remaining'])==5
    record(app,ctx,payload(ctx,quantity='58',corrects_public_id=first.public_id,expected_version=1,reason='Verified recount'))
    rows=delivery.listing(ctx['shipment'],_user(app))['cargo']
    assert Decimal(rows[0]['delivered'])==93 and Decimal(rows[0]['remaining'])==7
    record(app,ctx,payload(ctx,quantity='9'))
    rows=delivery.listing(ctx['shipment'],_user(app))['cargo']
    assert Decimal(rows[0]['delivered'])==102 and Decimal(rows[0]['excess'])==2
    assert not rows[1]['has_delivery'] and Decimal(rows[1]['delivered'])==0 and Decimal(rows[1]['remaining'])==25
    for row in (b,b_allocation,b_stage.execution_unit,shipment): db.session.refresh(row)
    after = (b.quantity,b.planned_quantity,b.actual_quantity,b.version,
        b_allocation.allocated_quantity,b_allocation.version,b_stage.execution_unit.lifecycle_status,
        b_stage.execution_unit.version,shipment.lifecycle_status,shipment.version,OperationalWorkItem.query.count())
    assert before == after and b_stage.execution_unit.lifecycle_status=='in_progress'
    result={'product_sha':product,'status':'PASS','database':'owned SQLite memory, explicit synthetic data',
        'A_effective_delivered_sequence':['95','93','102'],'A_remaining_sequence':['5','7','0'],'A_excess':'2',
        'B_current_actual_allocation':'25','B_unit_lifecycle':'in_progress','B_delivered':'0','B_remaining':'25',
        'B_quantities_allocation_unit_version_unchanged':True,'shipment_status_version_unchanged':True,
        'work_items_unchanged':True,'production_accessed':False,'recorded_at_utc':datetime.now(timezone.utc).isoformat()}
    db.session.remove(); db.engine.dispose()
fixture.close()
Path(__file__).with_name('active-transit-scenario.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
