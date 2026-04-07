from operaciones.application.results import UseCaseResult
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


def registrar_planilla_desv_semillas(
    payload: dict, *, repos: Repositories | None = None
) -> UseCaseResult:
    """
    Persiste una planilla de semillas desverdizado via repositorio.
    Funciona con PERSISTENCE_BACKEND=sqlite y PERSISTENCE_BACKEND=dataverse.

    payload esperado:
      lote_id      : PK del lote
      operator_code: str
      source_system: str (default "web")
      extra        : dict con todos los campos de la planilla
    """
    if repos is None:
        repos = get_repositories()

    lote_id = payload.get("lote_id")
    if not lote_id:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="lote_id es requerido",
            errors=["lote_id es requerido"],
        )

    record = repos.planillas_desv_semillas.create(
        lote_id,
        operator_code=payload.get("operator_code", ""),
        source_system=payload.get("source_system", "web"),
        extra=payload.get("extra", {}),
    )

    return UseCaseResult.success(
        code="PLANILLA_DESV_SEMILLAS_REGISTRADA",
        message="Planilla de semillas desverdizado registrada",
        data={"id": record.id},
    )
