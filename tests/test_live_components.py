import hashlib
import json
import math

import httpx
import pytest
from openai import AsyncOpenAI
from qdrant_client import QdrantClient

from app.config import ROOT, Settings
from app.models import Incident
from app.providers import OpenAIProvider
from app.retrieval import HybridRetriever, load_chunks, tokens


async def fixture_embeddings(texts):
    # A deterministic test vector, explicitly not a semantic model.
    result = []
    for text in texts:
        vector = [0.0] * 256
        for token in tokens(text):
            index = int(hashlib.sha256(token.encode()).hexdigest()[:8], 16) % 256
            vector[index] += 1
        norm = math.sqrt(sum(v * v for v in vector)) or 1
        result.append([v / norm for v in vector])
    return result, 10


async def test_actual_qdrant_index_and_hybrid_retrieval():
    client = QdrantClient(":memory:")
    retriever = HybridRetriever(
        load_chunks(ROOT / "runbooks"), client, fixture_embeddings, "test", 256
    )
    assert await retriever.initialize() > 0
    assert await retriever.initialize() == 0  # Reuse an identical complete index.
    sources, usage = await retriever.retrieve("OOMKilled memory limit")
    assert "oom" in {s.runbook for s in sources}
    assert usage == 10
    assert client.count(retriever.collection, exact=True).count == len(retriever.chunks)
    client.close()


async def test_qdrant_rejects_bad_embedding_shape():
    async def bad(_texts):
        return [[0.0]], 0

    client = QdrantClient(":memory:")
    retriever = HybridRetriever(load_chunks(ROOT / "runbooks"), client, bad, "bad", 256)
    with pytest.raises(ValueError, match="shape"):
        await retriever.initialize()
    client.close()


async def test_openai_sdk_request_and_structured_response_contract():
    captured = []

    def handler(request):
        body = json.loads(request.content)
        captured.append((request.url.path, body))
        if request.url.path.endswith("embeddings"):
            return httpx.Response(
                200,
                json={
                    "object": "list",
                    "data": [{"object": "embedding", "index": 0, "embedding": [0.1] * 256}],
                    "model": "text-embedding-3-small",
                    "usage": {"prompt_tokens": 3, "total_tokens": 3},
                },
            )
        diagnosis = {
            "summary": "More evidence needed",
            "confidence": "low",
            "insufficient_evidence": True,
            "hypotheses": [],
            "checks": [],
            "missing_information": ["Previous logs"],
        }
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": "gpt-4.1-mini",
                "error": None,
                "incomplete_details": None,
                "output": [
                    {
                        "id": "msg_test",
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(diagnosis),
                                "annotations": [],
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 40, "output_tokens": 20, "total_tokens": 60},
            },
        )

    provider = OpenAIProvider(Settings(mode="live", api_key="test-key", dimensions=256))
    await provider.client.close()
    provider.client = AsyncOpenAI(
        api_key="test-key",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False),
    )
    vectors, usage = await provider.embed(["CrashLoopBackOff"])
    assert len(vectors[0]) == 256 and usage == 3
    diagnosis, inp, out = await provider.diagnose(
        Incident(title="Unknown crash", events="CrashLoopBackOff"), []
    )
    assert diagnosis.insufficient_evidence and (inp, out) == (40, 20)
    request = captured[-1][1]
    assert request["store"] is False
    assert request["text"]["format"]["strict"] is True
    assert request["text"]["format"]["schema"]["additionalProperties"] is False
    await provider.close()
