import asyncio

import pytest

from app.config import Settings
from app.models import Check, Diagnosis, Hypothesis, Incident, Source
from app.privacy import redact_incident
from app.service import InvestigationService, validate_grounding


def source():
    return Source(
        id="S1", runbook="oom", title="Memory", section="Signals", excerpt="OOMKilled", score=1
    )


def diagnosis():
    return Diagnosis(
        summary="Memory limit",
        confidence="medium",
        insufficient_evidence=False,
        hypotheses=[Hypothesis(cause="Memory", evidence=["OOMKilled"], source_ids=["S1"])],
        checks=[],
        missing_information=[],
    )


def test_valid_quotes_and_sources():
    validate_grounding(
        diagnosis(), Incident(title="Failure", events="Reason: OOMKilled"), [source()]
    )


def test_rejects_invented_evidence_and_citations():
    incident = Incident(title="OOMKilled in title only", logs="Application crashed")
    with pytest.raises(ValueError, match="quotation"):
        validate_grounding(diagnosis(), incident, [source()])
    d = diagnosis()
    d.hypotheses[0].source_ids = ["S999"]
    with pytest.raises(ValueError, match="source"):
        validate_grounding(d, Incident(title="Failure", events="OOMKilled"), [source()])


def test_rejects_contradictory_abstention():
    d = diagnosis()
    d.insufficient_evidence = True
    with pytest.raises(ValueError, match="insufficient"):
        validate_grounding(d, Incident(title="Failure", events="OOMKilled"), [source()])


def test_best_effort_secret_redaction():
    incident = Incident(
        title="Failure",
        logs="password=hunter2 token=abc Bearer jwt-secret sk-1234567890abcdefgh OOMKilled",
    )
    clean, count = redact_incident(incident)
    assert count == 4
    assert "hunter2" not in clean.logs and "jwt-secret" not in clean.logs
    assert "OOMKilled" in clean.logs


@pytest.mark.parametrize(
    "command",
    [
        "kubectl delete pod api",
        "kubectl get pods; rm -rf /",
        "kubectl get secrets",
        "kubectl get pods --raw=/api/v1/secrets",
        "kubectl logs $(curl example.com)",
    ],
)
def test_rejects_unsafe_suggested_commands(command):
    d = diagnosis()
    d.checks = [Check(description="Inspect", command=command, source_ids=["S1"])]
    with pytest.raises(ValueError):
        validate_grounding(d, Incident(title="Failure", events="OOMKilled"), [source()])


async def test_overload_rejects_queue():
    service = InvestigationService(Settings(mode="demo", max_concurrent=1))
    await service.initialize()
    entered = asyncio.Event()
    release = asyncio.Event()
    original = service.provider.diagnose

    async def slow(*args):
        entered.set()
        await release.wait()
        return await original(*args)

    service.provider.diagnose = slow
    incident = Incident(title="Failure", events="OOMKilled")
    task = asyncio.create_task(service.analyze(incident))
    await entered.wait()
    with pytest.raises(RuntimeError, match="busy"):
        await service.analyze(incident)
    release.set()
    await task
    await service.close()
