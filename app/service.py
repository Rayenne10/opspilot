import asyncio
import re
import shlex
import time
import uuid

from prometheus_client import CollectorRegistry, Counter, Histogram
from qdrant_client import QdrantClient

from app.models import AnalysisResponse
from app.privacy import redact_incident
from app.providers import DemoProvider, OpenAIProvider
from app.retrieval import BM25, HybridRetriever, load_chunks


class ServiceUnavailable(RuntimeError):
    """A safe, application-owned availability message."""


def validate_grounding(diagnosis, incident, sources):
    allowed = {s.id for s in sources}
    if len(diagnosis.hypotheses) > 3 or len(diagnosis.checks) > 6:
        raise ValueError("Response exceeds hypothesis/check limits")
    if diagnosis.insufficient_evidence:
        if (
            diagnosis.hypotheses
            or diagnosis.confidence != "low"
            or not diagnosis.missing_information
        ):
            raise ValueError("Invalid insufficient-evidence response")
    elif not diagnosis.hypotheses:
        raise ValueError("A supported diagnosis needs hypotheses")
    for hypothesis in diagnosis.hypotheses:
        if not hypothesis.source_ids or not set(hypothesis.source_ids) <= allowed:
            raise ValueError("Hypothesis has invalid source references")
        if not hypothesis.evidence or any(
            not quote.strip() or quote not in incident.evidence_text()
            for quote in hypothesis.evidence
        ):
            raise ValueError("Evidence quotation is not present in the submitted incident")
    for check in diagnosis.checks:
        if not check.source_ids or not set(check.source_ids) <= allowed:
            raise ValueError("Check has invalid source references")
        if check.command:
            # Recommendations are never executed. Restrict even displayed commands to
            # a small read-only kubectl vocabulary, rejecting compound shell commands.
            command = re.sub(
                r"<(pod|namespace|node|service|pvc|policy|container)>", "PLACEHOLDER", check.command
            )
            if re.search(r"[;&|`$\\\r\n<>]", command):
                raise ValueError("Suggested command contains shell operators")
            parts = shlex.split(command)
            if (
                len(parts) < 3
                or parts[0] != "kubectl"
                or parts[1] not in {"get", "describe", "logs", "top"}
            ):
                raise ValueError("Only read-only kubectl checks are allowed")
            if any(
                arg.split("=")[0]
                in {"--raw", "--kubeconfig", "--token", "--client-key", "--client-certificate"}
                for arg in parts
            ):
                raise ValueError("Suggested command contains a disallowed flag")
            if parts[1] in {"get", "describe"} and parts[2] in {"secret", "secrets"}:
                raise ValueError("Secret commands are not allowed")


class InvestigationService:
    def __init__(self, settings):
        settings.validate()
        self.settings = settings
        self.chunks = load_chunks(settings.runbooks)
        self.provider = DemoProvider() if settings.mode == "demo" else OpenAIProvider(settings)
        self.vector_client = None
        if settings.mode == "live":
            self.vector_client = QdrantClient(
                url=settings.qdrant_url, api_key=settings.qdrant_key or None, timeout=20
            )
            self.retriever = HybridRetriever(
                self.chunks,
                self.vector_client,
                self.provider.embed,
                settings.embedding_model,
                settings.dimensions,
            )
        else:
            self.retriever = BM25(self.chunks)
        self.semaphore = asyncio.Semaphore(settings.max_concurrent)
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "opspilot_investigations_total",
            "Completed investigations",
            ["mode", "status"],
            registry=self.registry,
        )
        self.latency = Histogram(
            "opspilot_investigation_seconds",
            "Investigation latency",
            ["mode"],
            registry=self.registry,
        )
        self.tokens = Counter(
            "opspilot_tokens_total", "Provider token usage", ["kind"], registry=self.registry
        )
        self.redactions = Counter(
            "opspilot_redactions_total", "Best-effort secret redactions", registry=self.registry
        )
        self.ready = False

    async def initialize(self):
        if self.settings.mode == "live":
            # Allow the vector service a short startup window in Compose/Kubernetes.
            for attempt in range(12):
                try:
                    await asyncio.to_thread(self.vector_client.get_collections)
                    break
                except Exception:
                    if attempt == 11:
                        raise
                    await asyncio.sleep(2)
            used = await self.retriever.initialize()
            self.tokens.labels("embedding_index").inc(used)
        self.ready = True

    async def analyze(self, incident):
        if not self.ready:
            raise ServiceUnavailable("Index is not ready")
        start = time.perf_counter()
        try:
            # Reject overload instead of building an unbounded queue of paid model requests.
            await asyncio.wait_for(self.semaphore.acquire(), timeout=0.1)
        except TimeoutError as error:
            self.requests.labels(self.settings.mode, "busy").inc()
            raise ServiceUnavailable("The service is busy; retry shortly") from error
        try:
            clean, redactions = redact_incident(incident)
            self.redactions.inc(redactions)
            sources, embedded = await self.retriever.retrieve(clean.retrieval_text())
            self.tokens.labels("embedding_query").inc(embedded)
            diagnosis, input_tokens, output_tokens = await self.provider.diagnose(clean, sources)
            self.tokens.labels("input").inc(input_tokens)
            self.tokens.labels("output").inc(output_tokens)
            validate_grounding(diagnosis, clean, sources)
            elapsed = time.perf_counter() - start
            self.requests.labels(self.settings.mode, "ok").inc()
            self.latency.labels(self.settings.mode).observe(elapsed)
            return AnalysisResponse(
                request_id=str(uuid.uuid4()),
                mode=self.settings.mode,
                retrieval="bm25" if self.settings.mode == "demo" else "hybrid",
                diagnosis=diagnosis,
                sources=sources,
                latency_ms=round(elapsed * 1000, 2),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                embedding_tokens=embedded,
                redactions=redactions,
                notice="Demo uses deterministic rules, not an LLM."
                if self.settings.mode == "demo"
                else "AI suggestions require engineer review. Citations and evidence quotes are validated; factual correctness is not guaranteed.",
            )
        except Exception:
            self.requests.labels(self.settings.mode, "error").inc()
            raise
        finally:
            self.semaphore.release()

    async def close(self):
        self.ready = False
        if self.vector_client:
            self.vector_client.close()
        if self.settings.mode == "live":
            await self.provider.close()
