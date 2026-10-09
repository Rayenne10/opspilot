from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Incident(StrictModel):
    title: str = Field(min_length=3, max_length=160)
    namespace: str = Field(default="default", pattern=r"^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$")
    symptom: str = Field(default="", max_length=2000)
    logs: str = Field(default="", max_length=20000)
    events: str = Field(default="", max_length=20000)

    @model_validator(mode="after")
    def has_evidence(self):
        if not (self.logs.strip() or self.events.strip() or self.symptom.strip()):
            raise ValueError("Provide a symptom, logs, or Kubernetes events")
        return self

    def evidence_text(self) -> str:
        return "\n".join([self.symptom, self.logs, self.events])

    def retrieval_text(self) -> str:
        return self.title + "\n" + self.evidence_text()


class Hypothesis(StrictModel):
    cause: str
    evidence: list[str]
    source_ids: list[str]


class Check(StrictModel):
    description: str
    command: str
    source_ids: list[str]


class Diagnosis(StrictModel):
    summary: str
    confidence: Literal["low", "medium", "high"]
    insufficient_evidence: bool
    hypotheses: list[Hypothesis]
    checks: list[Check]
    missing_information: list[str]


class Source(StrictModel):
    id: str
    runbook: str
    title: str
    section: str
    excerpt: str
    score: float


class AnalysisResponse(StrictModel):
    request_id: str
    mode: Literal["demo", "live"]
    retrieval: Literal["bm25", "hybrid"]
    diagnosis: Diagnosis
    sources: list[Source]
    latency_ms: float
    input_tokens: int
    output_tokens: int
    embedding_tokens: int
    redactions: int
    notice: str
