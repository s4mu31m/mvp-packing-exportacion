"""
Telemetría liviana para llamadas Dataverse.

Cuenta y cronometra las llamadas HTTP al Web API de Dataverse por request Django.
Solo loggea si se supera un umbral para evitar ruido en operación normal.

Uso en DataverseClient._request():
    from .telemetry import record_dv_call
    record_dv_call(elapsed_ms)

Uso en middleware:
    from infrastructure.dataverse.telemetry import start_dv_tracking, end_dv_tracking
"""
import threading
import logging

_local = threading.local()
_log = logging.getLogger("dataverse.perf")

# Umbrales para emitir warning
_MAX_CALLS_WARN = 5
_MAX_MS_WARN = 2000.0


def start_dv_tracking() -> None:
    """Inicializa contadores para el request actual."""
    _local.calls = 0
    _local.total_ms = 0.0


def record_dv_call(elapsed_ms: float) -> None:
    """Registra una llamada completada (llamar desde DataverseClient._request)."""
    _local.calls = getattr(_local, "calls", 0) + 1
    _local.total_ms = getattr(_local, "total_ms", 0.0) + elapsed_ms


def end_dv_tracking(path: str) -> None:
    """
    Loggea resumen del request si supera umbrales.
    path: request.path de Django para identificar la vista.
    """
    calls = getattr(_local, "calls", 0)
    total_ms = getattr(_local, "total_ms", 0.0)
    if calls > _MAX_CALLS_WARN or total_ms > _MAX_MS_WARN:
        _log.warning(
            "PERF [%s] → %d llamadas Dataverse, %.0fms total",
            path, calls, total_ms,
        )
    else:
        _log.debug(
            "PERF [%s] → %d llamadas Dataverse, %.0fms total",
            path, calls, total_ms,
        )
