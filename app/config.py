import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    mode: str = field(default_factory=lambda: os.getenv("OPSPILOT_MODE", "demo"))
    api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    embedding_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    )
    dimensions: int = field(
        default_factory=lambda: int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "1536"))
    )
    qdrant_url: str = field(
        default_factory=lambda: os.getenv("QDRANT_URL", "http://localhost:6333")
    )
    qdrant_key: str = field(default_factory=lambda: os.getenv("QDRANT_API_KEY", ""))
    api_token: str = field(default_factory=lambda: os.getenv("OPSPILOT_API_TOKEN", ""))
    max_concurrent: int = field(
        default_factory=lambda: int(os.getenv("OPSPILOT_MAX_CONCURRENT", "2"))
    )
    runbooks: Path = ROOT / "runbooks"
    static: Path = ROOT / "static"
    fixtures: Path = ROOT / "evaluation" / "incidents.json"

    def validate(self):
        if self.mode not in {"demo", "live"}:
            raise ValueError("OPSPILOT_MODE must be demo or live")
        if self.mode == "live" and not self.api_key:
            raise ValueError("Live mode requires OPENAI_API_KEY")
        if not 1 <= self.max_concurrent <= 16:
            raise ValueError("OPSPILOT_MAX_CONCURRENT must be between 1 and 16")
        if not 256 <= self.dimensions <= 3072:
            raise ValueError("Embedding dimensions must be between 256 and 3072")
