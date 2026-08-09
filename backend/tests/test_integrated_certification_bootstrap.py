from pathlib import Path


def test_bootstrap_contract_is_guarded_and_secret_safe():
    root=Path(__file__).resolve().parents[2]
    source=(root/"scripts/integrated_certification_bootstrap.py").read_text(encoding="utf-8")
    contract=(root/"docs/operational/integrated-certification-bootstrap.md").read_text(encoding="utf-8")
    assert "forwarder_integrated_cert_" in source
    assert "FORWARDER_CERT_PASSWORD" in source
    assert "Production" in contract and "Derived state" in contract
    assert '"route_exception.read"' in source
    result_block=source[source.index('return {"schema_version"'):source.index("\n\n\ndef main")]
    assert "password" not in result_block.lower()
