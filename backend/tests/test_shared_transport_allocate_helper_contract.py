"""Static guardrails for the mutation-aware shared allocation E2E helper."""

from pathlib import Path


SPEC = Path(__file__).parents[2] / "e2e" / "shared-transport.spec.ts"


def _helper_source() -> str:
    source = SPEC.read_text(encoding="utf-8")
    return source[source.index("async function allocate"):source.index("\ntest.describe.serial")]


def test_allocate_waits_for_the_matching_cargo_mutation():
    helper = _helper_source()
    assert "page.waitForResponse" in helper
    assert 'request.method() !== "POST"' in helper
    assert 'pathname.endsWith("/allocations")' in helper
    assert "request.postDataJSON()?.cargo_public_id === cargoId" in helper


def test_allocate_waits_for_cargo_specific_refreshed_ui_state():
    helper = _helper_source()
    assert 'getByRole("option", {name: cargoLabel, exact: true})' in helper
    assert ").toHaveCount(0)" in helper
    assert 'getByRole("listitem").filter({hasText: cargoDescription})' in helper
    assert ").toBeVisible()" in helper


def test_allocate_cannot_return_before_response_and_post_state():
    helper = _helper_source()
    response = helper.index("await responsePromise")
    eligible_removed = helper.index(").toHaveCount(0)")
    allocation_visible = helper.index(").toBeVisible()")
    assert response < eligible_removed < allocation_visible


def test_allocate_fails_closed_on_unsuccessful_response():
    helper = _helper_source()
    assert "expect(response.status()" in helper
    assert ").toBe(201)" in helper
    assert "Allocation mutation failed for ${cargoId}" in helper


def test_allocate_has_no_sleep_retry_or_timeout_inflation():
    helper = _helper_source()
    assert "waitForTimeout" not in helper
    assert "setTimeout" not in helper
    assert "timeout:" not in helper
    assert "retry" not in helper.lower()
