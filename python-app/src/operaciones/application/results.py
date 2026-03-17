from dataclasses import dataclass, field
from typing import Any


@dataclass
class UseCaseResult:
    ok: bool
    code: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @classmethod
    def success(cls, code: str, message: str, data: dict | None = None):
        return cls(
            ok=True,
            code=code,
            message=message,
            data=data or {},
            errors=[],
        )

    @classmethod
    def reject(cls, code: str, message: str, errors: list[str] | None = None, data: dict | None = None):
        return cls(
            ok=False,
            code=code,
            message=message,
            data=data or {},
            errors=errors or [],
        )
