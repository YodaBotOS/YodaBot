import datetime
from dataclasses import dataclass, field


def from_iso(iso: str = None):
    if not iso:
        return None
    
    return datetime.datetime.fromisoformat(iso.rstrip("Z"))


@dataclass()
class ReplicateResult:
    id: str
    version: str
    status: str
    urls: dict = field(default_factory=dict, init=True)
    created_at: datetime.datetime = field(default_factory=from_iso, init=True)
    started_at: datetime.datetime | None = field(default_factory=from_iso, init=True)
    completed_at: datetime.datetime | None = field(default_factory=from_iso, init=True)
    source: str | None = None
    input: dict = field(default_factory=dict, init=True)
    output: list[str] = field(default_factory=list, init=True)
    error: str | None = None
    logs: str | None = None
    metrics: dict = field(default_factory=dict, init=True)
