# Levantamiento

> Referencia completa: [02 Flujo operativo y trazabilidad — Wiki](https://github.com/s4mu31m/mvp-packing-exportacion/wiki/02-Flujo-operativo-y-trazabilidad)

---

## Cambio operativo relevante

El flujo actualizado asume que los bins llegan **preconstruidos** desde el módulo anterior. Por lo tanto, este módulo no los genera: los recibe y los utiliza como base de trazabilidad.

---

## Flujo operativo mínimo vigente

El siguiente flujo es el mínimo vigente del proceso. Ninguna de sus etapas puede omitirse del contrato funcional. Si una etapa no está implementada técnicamente, se considera pendiente de implementación, no exclusión del negocio.

```
Fruta a granel
    → Recepción en planta
    → Pesaje y creación/asignación de lote planta

    ¿La fruta requiere desverdizado?
        No → Ingreso a packing
        Sí → ¿Disponibilidad en cámara de desverdizado?
                No → Espera en cámara de mantención / prefrío → (vuelve a preguntar disponibilidad)
                Sí → Proceso de desverdizado
                       → Control de calidad posterior a desverdizado
                       → Ingreso a packing

    Ingreso a packing
    → Armado de pallet
    → Control de calidad posterior a pallet
    → Ingreso a cámara de frío
    → Control de temperatura
```

---

## Definiciones obligatorias sobre el flujo

### Desverdizado

El desverdizado es una etapa fundamental del flujo y no puede ser pasada por alto. Su ausencia en una implementación no implica exclusión funcional: si aún no está implementado, debe quedar marcado como pendiente técnica, nunca como exclusión del negocio.

### Controles de calidad

Los controles de calidad forman parte del flujo mínimo actual. En este corte solo se implementará un alcance mínimo, especialmente para control de cítricos. No se implementarán al 100% todas sus variantes por tipo de fruta en esta etapa.

### Control de temperatura

Es un control asociado, no una macroetapa equivalente a recepción, packing o cámara.

---

## Nomenclatura del flujo

| Nombre explicativo | Nombre técnico |
|---|---|
| Recepción en planta | `recepcion_planta` |
| Creación/asignación de lote planta | `lote_planta` |
| Espera en cámara de mantención / prefrío | `camara_mantencion` |
| Proceso de desverdizado | `desverdizado` |
| Control de calidad posterior a desverdizado | `calidad_desverdizado` |
| Ingreso a packing | `ingreso_a_packing` |
| Armado de pallet | `pallet` / `paletizaje` según contexto |
| Control de calidad posterior a pallet | `calidad_pallet` |
| Ingreso a cámara de frío | `camara_frio` |
| Control de temperatura | `medicion_temperatura_salida` |

---

## Eje de trazabilidad

La trazabilidad mínima del MVP debe responder:

- ¿Qué bin ingresó?
- ¿A qué lote quedó asociado?
- ¿Por qué etapas pasó?
- ¿Quién registró cada evento?
- ¿Qué controles de calidad tuvo?
- ¿Terminó como fruta comercial o fruta de exportación?
- ¿Si fue exportación, en qué cámara, pallet o embarque quedó?

La unidad documental mínima es: **Bin → Lote → Etapa**

Y cuando corresponde, se extiende a: **Bin → Lote → Etapa → Pallet / Cámara de frío**

---

## Actores del flujo

- **Operador de recepción:** registra bins recibidos y crea lotes.
- **Operador de packing:** registra eventos de etapa durante el proceso.
- **Jefatura:** consulta trazabilidad y estado operativo.

---

## Restricciones identificadas

- El bin es único por temporada.
- Un bin puede pertenecer a un solo lote.
- El lote puede identificarse sin ambigüedad dentro de la campaña.
- No todas las etapas requerirán tabla especializada en la primera entrega.
- Los controles de calidad se modelan como eventos flexibles asociados a etapas.

---

## Contrato de integración con bins preconstruidos

El módulo debe definir con el upstream:

- Formato oficial del código de bin.
- Unicidad esperada por temporada.
- Campos obligatorios de entrada.
- Relación esperada entre bin y lote.
- Tratamiento de duplicados (estrategia **strict** recomendada en integraciones automáticas).
- Política de corrección de errores aguas arriba.
