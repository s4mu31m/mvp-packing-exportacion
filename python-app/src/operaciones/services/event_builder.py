from operaciones.models import RegistroEtapa


def build_event_key(*parts: str) -> str:
    clean_parts = [str(p).strip().upper() for p in parts if str(p).strip()]
    return "-".join(clean_parts)


def create_registro_etapa(
    *,
    temporada: str,
    event_key: str,
    tipo_evento: str,
    bin_obj=None,
    lote_obj=None,
    pallet_obj=None,
    operator_code: str = "",
    source_system: str = "local",
    source_event_id: str = "",
    payload: dict | None = None,
):
    return RegistroEtapa.objects.create(
        temporada=temporada,
        event_key=event_key,
        tipo_evento=tipo_evento,
        bin=bin_obj,
        lote=lote_obj,
        pallet=pallet_obj,
        operator_code=operator_code,
        source_system=source_system,
        source_event_id=source_event_id,
        payload=payload or {},
    )
