from dataclasses import dataclass, field, asdict
from typing import Any


class DataError(ValueError):
    """An actionable input error, without leaking a parser traceback to CLI users."""


@dataclass
class Report:
    provenance: dict[str, Any]
    selection: dict[str, Any] = field(default_factory=dict)
    input_rows: int = 0
    selected_rows: int = 0
    issues: list[dict[str, Any]] = field(default_factory=list)
    transformations: list[dict[str, Any]] = field(default_factory=list)

    def add(self, severity: str, code: str, message: str, row: int | None = None) -> None:
        self.issues.append(dict(severity=severity, code=code, message=message, row=row))

    @property
    def valid(self) -> bool:
        return not any(i['severity'] == 'error' for i in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return dict(asdict(self), valid=self.valid)


@dataclass
class Dataset:
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    report: Report
    period: str
