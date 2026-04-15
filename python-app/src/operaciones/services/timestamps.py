"""
Helper para timestamps operativos.

Centraliza la generacion del timestamp UTC usado en cada transicion de etapa,
de modo que los use cases no dupliquen la llamada a datetime.now().
"""
from datetime import datetime, timezone


def ahora_utc() -> str:
    """
    Retorna el timestamp UTC actual en formato ISO 8601 para Dataverse.

    Dataverse acepta DateTime en formato 'YYYY-MM-DDTHH:MM:SSZ'.
    Este valor se escribe en crf21_ultimo_cambio_estado_at cada vez
    que un use case transiciona etapa_actual en un Lote o Pallet.
    """
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
