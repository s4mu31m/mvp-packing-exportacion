"""
Caso de uso: Eliminar Bin de Lote Abierto

Elimina un bin de un lote abierto usando la capa de repositorios,
compatible con los backends SQLite y Dataverse.

Flujo:
  1. Localizar lote y verificar que este abierto.
  2. Localizar el bin por codigo.
  3. Verificar que el bin pertenece al lote (BinLote).
  4. Eliminar BinLote primero (libera la FK PROTECT en SQLite).
  5. Eliminar Bin.
  6. Decrementar lote.cantidad_bins.
"""
from operaciones.application.results import UseCaseResult
from operaciones.models import LotePlantaEstado
from operaciones.services.normalizers import normalize_code, normalize_temporada
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


def eliminar_bin_de_lote(payload: dict, *, repos: Repositories | None = None) -> UseCaseResult:
    if repos is None:
        repos = get_repositories()

    temporada = normalize_temporada(payload.get("temporada", ""))
    lote_code  = normalize_code(payload.get("lote_code", ""))
    bin_code   = normalize_code(payload.get("bin_code", ""))

    if not lote_code or not bin_code:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="lote_code y bin_code son requeridos",
            errors=["lote_code y bin_code son requeridos"],
        )

    # Verificar lote existe y esta abierto
    lote = repos.lotes.find_by_code(temporada, lote_code)
    if not lote:
        return UseCaseResult.reject(
            code="LOTE_NOT_FOUND",
            message=f"No existe el lote {lote_code}",
            errors=[f"Lote no encontrado: {lote_code}"],
        )
    if lote.estado != LotePlantaEstado.ABIERTO:
        return UseCaseResult.reject(
            code="LOTE_NOT_OPEN",
            message=f"El lote {lote_code} no esta abierto (estado: {lote.estado})",
            errors=[f"El lote debe estar en estado '{LotePlantaEstado.ABIERTO}' para eliminar bins"],
        )

    # Localizar el bin
    bin_record = repos.bins.find_by_code(temporada, bin_code)
    if not bin_record:
        return UseCaseResult.reject(
            code="BIN_NOT_FOUND",
            message=f"No existe el bin {bin_code}",
            errors=[f"Bin no encontrado: {bin_code}"],
        )

    # Verificar que el bin pertenece al lote
    bin_lote = repos.bin_lotes.find_by_bin_and_lote(bin_record.id, lote.id)
    if not bin_lote:
        return UseCaseResult.reject(
            code="BIN_NOT_IN_LOTE",
            message=f"El bin {bin_code} no pertenece al lote {lote_code}",
            errors=[f"Bin {bin_code} no encontrado en el lote {lote_code}"],
        )

    # Eliminar BinLote primero (libera la FK PROTECT sobre Bin en SQLite)
    repos.bin_lotes.delete(bin_lote.id)
    # Eliminar Bin
    repos.bins.delete(bin_record.id)

    # Decrementar contador en el lote
    nueva_cantidad = max(lote.cantidad_bins - 1, 0)
    repos.lotes.update(lote.id, {"cantidad_bins": nueva_cantidad})

    return UseCaseResult.success(
        code="BIN_ELIMINADO",
        message=f"Bin {bin_code} eliminado del lote {lote_code}",
        data={
            "bin_code": bin_code,
            "lote_code": lote_code,
            "cantidad_bins_restantes": nueva_cantidad,
        },
    )
