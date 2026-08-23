import json

import pytest

from backend import create_app
from backend.extensions import db
from backend.global_logistics_point_catalog import (
    APPROVED_CHECKSUM,
    CATALOG_PATH,
    CATALOG_VERSION,
    GlobalCatalogApplyError,
    GlobalCatalogValidationError,
    apply_catalog,
    canonical_checksum,
    load_catalog,
    plan_catalog,
)
from backend.global_logistics_point_catalog_cli import main as cli_main
from backend.global_logistics_point_models import (
    GlobalLogisticsPoint,
    GlobalLogisticsPointCorridorTag,
    GlobalLogisticsPointExternalCode,
    GlobalLogisticsPointMode,
    GlobalLogisticsPointSource,
)
from backend.logistics_network_models import LogisticsPointType
from backend.models import Country, ExpertUser, ReferenceDataSeedRun


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "APP_ENV": "testing",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "global-catalog-test",
        },
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def prepare_dependencies(
    authority="PLATFORM_ADMIN", active=True, username="platformadmin"
):
    actor = ExpertUser(
        username=username,
        password_hash="x",
        full_name="Platform Admin",
        role="admin",
        authority=authority,
        is_active=active,
    )
    db.session.add(actor)
    db.session.flush()
    catalog = load_catalog()
    countries = sorted({x["runtime_candidate"]["country_code"] for x in catalog.rows})
    types = sorted({x["runtime_candidate"]["point_type_code"] for x in catalog.rows})
    db.session.add_all([Country(code=x, name_en=x, name_fa=x) for x in countries])
    db.session.add_all(
        [
            LogisticsPointType(
                immutable_code=x,
                fa_name=x,
                en_name=x,
                definition=x,
                display_order=i,
                created_by=actor.id,
                updated_by=actor.id,
            )
            for i, x in enumerate(types)
        ]
    )
    db.session.commit()
    return actor, catalog


def apply(actor, catalog, failure_hook=None):
    return apply_catalog(
        catalog,
        environment="testing",
        operator=actor.username,
        approval_reference="ADR-041-OWNER-2026-08-23",
        expected_checksum=APPROVED_CHECKSUM,
        user_id=actor.id,
        failure_hook=failure_hook,
    )


def rewrite(tmp_path, mutate, *, recalculate=True):
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    mutate(payload)
    if recalculate:
        payload["checksum"] = canonical_checksum(payload)
    path = tmp_path / "package.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_approved_package_is_strict_exact_nine():
    catalog = load_catalog()
    assert (
        catalog.catalog_version == CATALOG_VERSION
        and catalog.checksum == APPROVED_CHECKSUM
    )
    assert len(catalog.rows) == 9


@pytest.mark.parametrize(
    "mutation",
    [
        lambda x: x["approved_global_logistics_points"].pop(),
        lambda x: x["approved_global_logistics_points"].append(
            x["approved_global_logistics_points"][0]
        ),
        lambda x: x["approved_global_logistics_points"][0]["runtime_candidate"].update(
            en_name="Modified"
        ),
        lambda x: x.update(unexpected=True),
    ],
)
def test_modified_missing_expanded_or_unexpected_package_is_rejected(
    tmp_path, mutation
):
    with pytest.raises(GlobalCatalogValidationError):
        load_catalog(rewrite(tmp_path, mutation))


def test_checksum_mismatch_and_original_39_row_package_are_rejected(tmp_path):
    with pytest.raises(GlobalCatalogValidationError, match="checksum"):
        load_catalog(
            rewrite(
                tmp_path,
                lambda x: x["approved_global_logistics_points"][0][
                    "runtime_candidate"
                ].update(en_name="Tampered"),
                recalculate=False,
            )
        )
    with pytest.raises(GlobalCatalogValidationError):
        load_catalog(
            CATALOG_PATH.with_name("global-logistics-points-china-iran-v1.0.0.json")
        )


def test_plan_apply_children_idempotency_and_evidence(app):
    with app.app_context():
        actor, catalog = prepare_dependencies()
        first = plan_catalog(catalog, "testing")
        assert (
            first.planned_count,
            first.created_count,
            first.unchanged_count,
            first.conflict_count,
        ) == (9, 9, 0, 0)
        assert (
            ReferenceDataSeedRun.query.count() == 0
            and GlobalLogisticsPoint.query.count() == 0
        )
        applied, run = apply(actor, catalog)
        assert run.status == "succeeded" and applied.created_count == 9
        assert GlobalLogisticsPoint.query.count() == 9
        assert {x.lifecycle_status for x in GlobalLogisticsPoint.query.all()} == {
            "DRAFT"
        }
        assert {x.verification_status for x in GlobalLogisticsPoint.query.all()} == {
            "UNVERIFIED"
        }
        assert all(
            (
                GlobalLogisticsPointMode.query.count(),
                GlobalLogisticsPointCorridorTag.query.count(),
                GlobalLogisticsPointExternalCode.query.count(),
                GlobalLogisticsPointSource.query.count(),
            )
        )
        second = plan_catalog(catalog, "testing")
        assert (
            second.created_count,
            second.unchanged_count,
            second.conflict_count,
        ) == (0, 9, 0)
        repeated, repeated_run = apply(actor, catalog)
        assert (
            repeated_run.status == "succeeded"
            and repeated.created_count == 0
            and repeated.unchanged_count == 9
        )
        assert (
            GlobalLogisticsPoint.query.count() == 9
            and ReferenceDataSeedRun.query.count() == 2
        )


@pytest.mark.parametrize(
    "authority,active",
    [("ORGANIZATION_ADMIN", True), ("EXPERT", True), ("PLATFORM_ADMIN", False)],
)
def test_only_active_platform_admin_may_apply(app, authority, active):
    with app.app_context():
        actor, catalog = prepare_dependencies(authority, active)
        with pytest.raises(GlobalCatalogApplyError, match="PLATFORM_ADMIN"):
            apply(actor, catalog)
        assert GlobalLogisticsPoint.query.count() == 0
        run = ReferenceDataSeedRun.query.one()
        assert run.status == "refused"


def test_operator_approval_and_checksum_are_explicit(app):
    with app.app_context():
        actor, catalog = prepare_dependencies()
        for values, message in [
            ({"operator": ""}, "operator"),
            ({"approval_reference": ""}, "approval"),
            ({"expected_checksum": "sha256:" + "0" * 64}, "checksum"),
        ]:
            kwargs = dict(
                environment="testing",
                operator=actor.username,
                approval_reference="A",
                expected_checksum=APPROVED_CHECKSUM,
                user_id=actor.id,
            )
            kwargs.update(values)
            with pytest.raises(GlobalCatalogApplyError, match=message):
                apply_catalog(catalog, **kwargs)


def test_conflict_refuses_all_catalog_writes_and_persists_evidence(app):
    with app.app_context():
        actor, catalog = prepare_dependencies()
        expected = catalog.rows[0]["runtime_candidate"]
        db.session.add(
            GlobalLogisticsPoint(
                immutable_code=expected["immutable_code"],
                point_type=LogisticsPointType.query.filter_by(
                    immutable_code=expected["point_type_code"]
                ).one(),
                country=Country.query.filter_by(code=expected["country_code"]).one(),
                fa_name="drift",
                en_name="drift",
                normalized_name="drift",
                geography_key=expected["geography_key"],
                facility_identity_key=expected["facility_identity_key"],
                lifecycle_status="DRAFT",
                verification_status="UNVERIFIED",
                created_by=actor.id,
                updated_by=actor.id,
            )
        )
        db.session.commit()
        plan, run = apply(actor, catalog)
        assert plan.conflict_count == 1 and run.status == "refused"
        assert GlobalLogisticsPoint.query.count() == 1


def test_failure_rolls_back_points_and_sanitizes_persisted_evidence(app):
    with app.app_context():
        actor, catalog = prepare_dependencies()

        def fail():
            raise RuntimeError("secret detail")

        with pytest.raises(GlobalCatalogApplyError, match="rolled back"):
            apply(actor, catalog, fail)
        assert GlobalLogisticsPoint.query.count() == 0
        run = ReferenceDataSeedRun.query.one()
        assert run.status == "failed"
        assert (
            "secret detail" not in run.error_summary
            and "RuntimeError" in run.error_summary
        )


def test_cli_plan_is_read_only_and_apply_requires_confirm(app, capsys):
    with app.app_context():
        actor, catalog = prepare_dependencies()
        actor_username, actor_id = actor.username, actor.id
    base = [
        "--catalog-version",
        CATALOG_VERSION,
        "--expected-checksum",
        APPROVED_CHECKSUM,
    ]
    assert cli_main(["plan", *base], app=app) == 0
    assert '"created_count": 9' in capsys.readouterr().out
    with app.app_context():
        assert ReferenceDataSeedRun.query.count() == 0
    assert (
        cli_main(
            [
                "apply",
                *base,
                "--operator",
                actor_username,
                "--approval-reference",
                "A",
                "--actor-user-id",
                str(actor_id),
            ],
            app=app,
        )
        == 2
    )
    assert "--confirm" in capsys.readouterr().err
