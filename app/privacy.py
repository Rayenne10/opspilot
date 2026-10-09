import re

from app.models import Incident

# Best-effort screening. It is not a substitute for reviewing operational logs.
PATTERNS = [
    re.compile(r"(?i)(\b(?:password|passwd|token|secret|api[_-]?key)\s*[=:]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(\bBearer\s+)([A-Za-z0-9._~+/=-]+)"),
    re.compile(r"()(\bsk-[A-Za-z0-9_-]{16,}\b)"),
    re.compile(r"()(\bAKIA[A-Z0-9]{16}\b)"),
    re.compile(r"()(-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----)"),
]


def redact(text: str) -> tuple[str, int]:
    count = 0
    for pattern in PATTERNS:
        text, n = pattern.subn(lambda m: m.group(1) + "[REDACTED]", text)
        count += n
    return text, count


def redact_incident(incident: Incident) -> tuple[Incident, int]:
    data = incident.model_dump()
    count = 0
    for key in ("title", "symptom", "logs", "events"):
        data[key], n = redact(data[key])
        count += n
    return Incident.model_validate(data), count
