from operaciones.application.results import UseCaseResult
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


def guardar_muestra_calidad_pallet(
    payload: dict, *, repos: Repositories | None = None
) -> UseCaseResult:
    """
    Persiste una muestra individual de calidad para un pallet via repositorio.
    Funciona con PERSISTENCE_BACKEND=sqlite y PERSISTENCE_BACKEND=dataverse.

    payload esperado:
      pallet_id    : PK del pallet
      operator_code: str
      source_system: str (default "web")
      extra        : dict con numero_muestra, temperatura_fruta,
                     peso_caja_muestra, n_frutos, aprobado, observaciones, rol
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

    record = repos.calidad_pallet_muestras.create(
        pallet_id,
        operator_code=payload.get("operator_code", ""),
        source_system=payload.get("source_system", "web"),
        extra=payload.get("extra", {}),
    )

    return UseCaseResult.success(
        code="MUESTRA_CALIDAD_REGISTRADA",
        message="Muestra de calidad registrada",
        data={"id": record.id, "numero_muestra": record.numero_muestra},
    )
