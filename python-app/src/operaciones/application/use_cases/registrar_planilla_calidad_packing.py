from operaciones.application.results import UseCaseResult
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


def registrar_planilla_calidad_packing(
    payload: dict, *, repos: Repositories | None = None
) -> UseCaseResult:
    """
    Persiste una planilla de calidad packing citricos via repositorio.
    Funciona con PERSISTENCE_BACKEND=sqlite y PERSISTENCE_BACKEND=dataverse.

    payload esperado:
      pallet_id    : PK del pallet
      operator_code: str
      source_system: str (default "web")
      extra        : dict con todos los campos de la planilla
    """
    if repos is None:
        repos = get_repositories()

    pallet_id = payload.get("pallet_id")
    if not pallet_id:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="pallet_id es requerido",
            errors=["pallet_id es requerido"],
        )

    record = repos.planillas_calidad_packing.create(
        pallet_id,
        operator_code=payload.get("operator_code", ""),
        source_system=payload.get("source_system", "web"),
        extra=payload.get("extra", {}),
    )

    return UseCaseResult.success(
        code="PLANILLA_CALIDAD_PACKING_REGISTRADA",
        message="Planilla de calidad packing registrada",
        data={"id": record.id},
    )
