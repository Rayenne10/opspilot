import asyncio
import hashlib
import math
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from qdrant_client import QdrantClient, models

from app.models import Source


@dataclass(frozen=True)
class Chunk:
    id: str
    runbook: str
    title: str
    section: str
    text: str


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9_-]*", text.lower())


def load_chunks(directory: Path) -> list[Chunk]:
    result = []
    for file in sorted(directory.glob("*.md")):
        content = file.read_text(encoding="utf-8")
        title = content.splitlines()[0].removeprefix("# ")
        sections = re.split(r"\n## ", content)
        for i, section in enumerate(sections):
            heading = "Overview" if i == 0 else section.splitlines()[0]
            # Character windows bound context while preserving a short overlap.
            for offset in range(0, len(section), 1400):
                text = section[offset : offset + 1600].strip()
                if not text:
                    continue
                cid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{file.name}:{i}:{offset}:{text}"))
                result.append(Chunk(cid, file.stem, title, heading, title + "\n" + text))
    if not result:
        raise ValueError("No runbooks found")
    return result


class BM25:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.terms = [Counter(tokens(c.text)) for c in chunks]
        self.lengths = [sum(t.values()) for t in self.terms]
        self.average = sum(self.lengths) / len(chunks)
        self.df = Counter(term for document in self.terms for term in document)

    def ranked(self, query: str, limit: int = 8) -> list[tuple[Chunk, float]]:
        scored = []
        for chunk, counts, length in zip(self.chunks, self.terms, self.lengths, strict=True):
            score = 0.0
            for term in set(tokens(query)):
                frequency = counts[term]
                if not frequency:
                    continue
                idf = math.log(1 + (len(self.chunks) - self.df[term] + 0.5) / (self.df[term] + 0.5))
                score += (
                    idf
                    * frequency
                    * 2.5
                    / (frequency + 1.5 * (0.25 + 0.75 * length / self.average))
                )
            if score > 0:
                scored.append((chunk, score))
        return sorted(scored, key=lambda pair: (-pair[1], pair[0].id))[:limit]

    async def retrieve(self, query: str, limit: int = 5) -> tuple[list[Source], int]:
        return as_sources(self.ranked(query, limit)), 0


def as_sources(ranked: list[tuple[Chunk, float]]) -> list[Source]:
    return [
        Source(
            id=f"S{i}",
            runbook=c.runbook,
            title=c.title,
            section=c.section,
            excerpt=c.text,
            score=round(score, 6),
        )
        for i, (c, score) in enumerate(ranked, 1)
    ]


class HybridRetriever:
    def __init__(
        self, chunks, client: QdrantClient, embedder, embedding_model: str, dimensions: int
    ):
        self.chunks = chunks
        self.by_id = {c.id: c for c in chunks}
        self.lexical = BM25(chunks)
        self.client = client
        self.embedder = embedder
        self.dimensions = dimensions
        fingerprint = hashlib.sha256(
            (embedding_model + str(dimensions) + "".join(c.id for c in chunks)).encode()
        ).hexdigest()[:16]
        self.collection = "opspilot_" + fingerprint

    async def initialize(self) -> int:
        exists = await asyncio.to_thread(self.client.collection_exists, self.collection)
        if exists:
            count = await asyncio.to_thread(self.client.count, self.collection, exact=True)
            if count.count == len(self.chunks):
                return 0
        else:
            await asyncio.to_thread(
                self.client.create_collection,
                self.collection,
                vectors_config=models.VectorParams(
                    size=self.dimensions, distance=models.Distance.COSINE
                ),
            )
        used = 0
        for offset in range(0, len(self.chunks), 32):
            batch = self.chunks[offset : offset + 32]
            vectors, usage = await self.embedder([c.text for c in batch])
            used += usage
            if len(vectors) != len(batch) or any(len(v) != self.dimensions for v in vectors):
                raise ValueError("Invalid embedding shape")
            points = [
                models.PointStruct(id=c.id, vector=v, payload={"runbook": c.runbook})
                for c, v in zip(batch, vectors, strict=True)
            ]
            await asyncio.to_thread(self.client.upsert, self.collection, points, wait=True)
        return used

    async def retrieve(self, query: str, limit: int = 5):
        vectors, usage = await self.embedder([query])
        if len(vectors) != 1 or len(vectors[0]) != self.dimensions:
            raise ValueError("Invalid query embedding shape")
        response = await asyncio.to_thread(
            self.client.query_points,
            self.collection,
            query=vectors[0],
            limit=limit * 2,
            with_payload=False,
        )
        dense = [str(p.id) for p in response.points if str(p.id) in self.by_id]
        lexical = [c.id for c, _ in self.lexical.ranked(query, limit * 2)]
        fusion = Counter()
        for ranking in (dense, lexical):
            for rank, cid in enumerate(ranking, 1):
                fusion[cid] += 1 / (60 + rank)
        ranked = sorted(fusion.items(), key=lambda pair: (-pair[1], pair[0]))[:limit]
        return as_sources([(self.by_id[cid], score) for cid, score in ranked]), usage
