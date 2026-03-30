"""
Gestion de correlativos para generacion automatica de codigos de negocio.

Usa SequenceCounter con select_for_update() para garantizar unicidad bajo
concurrencia en SQLite/PostgreSQL.

Para Dataverse: el correlativo debe obtenerse desde la tabla crf21_correlativos
(pendiente de implementacion OData completa). En esa etapa, reemplazar esta
funcion por una implementacion que consulte Dataverse y maneje retry ante
condiciones de carrera propias de la Web API.
"""
from django.db import transaction


def get_next_sequence(entity_name: str, dimension: str) -> int:
    """
    Devuelve el siguiente correlativo para la entidad y dimension dadas.

    entity_name: 'lote', 'bin' o 'pallet'.
    dimension:   clave de agrupacion del correlativo.
                 - Para 'lote': temporada_codigo (ej: '2025-2026').
                 - Para 'bin' y 'pallet': fecha YYYYMMDD (ej: '20260329').

    El correlativo es ascendente, nunca se reinicia dentro de la misma dimension,
    y no se reutiliza aunque el registro sea anulado.
    """
    from operaciones.models import SequenceCounter

    with transaction.atomic():
        obj, _ = SequenceCounter.objects.select_for_update().get_or_create(
            entity_name=entity_name,
            dimension=dimension,
            defaults={"last_value": 0},
        )
        obj.last_value += 1
        obj.save(update_fields=["last_value"])
        return obj.last_value
