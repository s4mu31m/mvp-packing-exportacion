"""
Caso de uso: Editar Bin de Lote Abierto

Actualiza los campos variables de un bin registrado en un lote abierto,
compatible con los backends SQLite y Dataverse.

Campos editables: numero_cuartel, hora_recepcion, kilos_bruto_ingreso,
                  kilos_neto_ingreso, a_o_r, observaciones.
Los campos base (codigo_productor, variedad_fruta, color, etc.) son inmutables.

La validacion de negocio kilos_neto <= kilos_bruto se hace a nivel de use case
para ser independiente del backend (Dataverse no tiene full_clean()).
"""
from decimal import Decimal, InvalidOperation

from operaciones.application.results import UseCaseResult
from operaciones.models import LotePlantaEstado
from operaciones.services.normalizers import normalize_code, normalize_temporada
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories

VARIABLE_FIELDS = frozenset({
    "numero_cuartel", "hora_recepcion", "kilos_bruto_ingreso",
    "kilos_neto_ingreso", "a_o_r", "observaciones",
})


def editar_bin_de_lote(payload: dict, *, repos: Repositories | None = None) -> UseCaseResult:
    if repos is None:
        repos = get_repositories()

    temporada = normalize_temporada(payload.get("temporada", ""))
    lote_code  = normalize_code(payload.get("lote_code", ""))
    bin_code   = normalize_code(payload.get("bin_code", ""))
    campos     = payload.get("campos", {})

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
            errors=[f"El lote debe estar en estado '{LotePlantaEstado.ABIERTO}' para editar bins"],
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

    # Filtrar solo campos permitidos
    campos_a_actualizar = {k: v for k, v in campos.items() if k in VARIABLE_FIELDS}

    # Validacion de negocio: kilos_neto <= kilos_bruto (backend-agnostico)
    try:
        kb = campos_a_actualizar.get("kilos_bruto_ingreso")
        kn = campos_a_actualizar.get("kilos_neto_ingreso")
        if kb is not None and kn is not None:
            if Decimal(str(kn)) > Decimal(str(kb)):
                return UseCaseResult.reject(
                    code="VALIDACION",
                    message="Kilos neto no puede superar kilos bruto",
                    errors=["kilos_neto_ingreso no puede superar kilos_bruto_ingreso."],
                )
    except (InvalidOperation, ValueError):
        return UseCaseResult.reject(
            code="VALIDACION",
            message="Valores de kilos invalidos",
            errors=["Los valores de kilos deben ser numericos."],
        )

    repos.bins.update(bin_record.id, campos_a_actualizar)

    return UseCaseResult.success(
        code="BIN_EDITADO",
        message=f"Bin {bin_code} actualizado correctamente",
        data={"bin_code": bin_code, "lote_code": lote_code},
    )
