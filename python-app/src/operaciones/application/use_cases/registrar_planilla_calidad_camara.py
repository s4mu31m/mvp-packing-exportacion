from operaciones.application.results import UseCaseResult
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


def registrar_planilla_calidad_camara(
    payload: dict, *, repos: Repositories | None = None
) -> UseCaseResult:
    """
    Persiste una planilla de control de camara via repositorio.
    Funciona con PERSISTENCE_BACKEND=sqlite y PERSISTENCE_BACKEND=dataverse.

    payload esperado:
      pallet_id    : PK del pallet (puede ser None si no se vincula a pallet especifico)
      operator_code: str
      source_system: str (default "web")
      extra        : dict con todos los campos de la planilla
    """
    if repos is None:
        repos = get_repositories()

    pallet_id = payload.get("pallet_id")  # puede ser None

    record = repos.planillas_calidad_camara.create(
        pallet_id,
        operator_code=payload.get("operator_code", ""),
        source_system=payload.get("source_system", "web"),
        extra=payload.get("extra", {}),
    )

    return UseCaseResult.success(
        code="PLANILLA_CALIDAD_CAMARA_REGISTRADA",
        message="Planilla de control de camara registrada",
        data={"id": record.id},
    )
