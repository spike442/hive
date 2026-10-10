from core.domain import PullRequest
from core.observability.audit import AuditLog


def test_shared_helpers_are_usable() -> None:
    audit = AuditLog()
    audit.record_model_response("response-1")
    assert audit.actions[0].action == "llm_response"


def test_pull_request_contract_keeps_optional_metadata_permissive() -> None:
    pull_request = PullRequest(
        owner="spike442",
        repository="homelab",
        number=0,
        base_sha="base",
        head_sha="head",
        clone_url="https://github.com/spike442/homelab.git",
    )
    assert pull_request.number == 0
    assert pull_request.labels == []
