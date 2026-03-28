# Alcance del MVP

> Referencia completa: [01 Alcance del MVP — Wiki](https://github.com/s4mu31m/mvp-packing-exportacion/wiki/01-Alcance-del-MVP)

---

## Enfoque general

El MVP corresponde a una **primera etapa funcional** de transición hacia una solución web propia, con backend Python y uso de Dataverse como sistema de registro principal.

---

## Objetivo de esta etapa

Entregar una solución operativa mínima, centrada en una etapa priorizada del flujo, con:

- Registro y actualización de información operativa
- Trazabilidad básica
- Consulta simple
- Exportación básica
- Uso real en terreno o en contexto operativo cercano

---

## Cambio operativo relevante: bins preconstruidos

En la versión actual del proyecto, los **bins ya no se construyen en este módulo**. Los bins llegan **preconstruidos** desde una etapa previa. Este módulo debe **recibir, validar, relacionar y trazar**.

El foco pasa desde "construcción" a **integración operativa + calidad de datos + trazabilidad**.

---

## Incluye

- Recepción de bins preconstruidos
- Validación de integridad del bin
- Upsert de bins y lotes
- Asociación bin → lote
- Registro por etapa
- Trazabilidad operacional por bin, lote y etapa
- Interfaz web responsive orientada a tablet
- Validaciones esenciales de negocio
- Control de acceso básico por perfil
- Vista simple de consulta para jefatura
- Exportación básica CSV o Excel
- Pruebas, despliegue y documentación mínima operativa

---

## No incluye en esta etapa

- Implementación completa de todo el flujo operacional
- Reportería avanzada
- Dashboards analíticos
- Automatizaciones complejas no prioritarias
- Reconstrucción lógica del bin dentro del módulo
- Migración histórica completa sin depuración previa
- Arquitectura enterprise completa
- IAM avanzado fuera de lo necesario para operar

---

## Criterio rector de alcance

El MVP debe priorizar:

1. Operación real
2. Trazabilidad mínima útil
3. Rapidez de captura
4. Integridad de datos
5. Viabilidad dentro del plazo disponible

---

## Resultado esperado al cierre

Al cierre del MVP debería existir una solución capaz de:

- Registrar una etapa priorizada
- Persistir correctamente la información
- Consultar trazabilidad mínima
- Exportar información básica
- Ser usada como base real de continuidad del proyecto

---

## Estado de implementación

| Componente | Estado |
|---|---|
| Modelo de datos base (Bin, Lote, Pallet, RegistroEtapa) | ✅ Implementado |
| Casos de uso: registrar_bin_recibido, crear_lote_recepcion, cerrar_pallet | ✅ Implementado y testeado |
| API REST básica (bins, lotes, pallets, eventos, trazabilidad) | ✅ Implementado |
| Interfaz web tablet-first funcional | 🔲 Pendiente |
| Consulta jefatura | 🔲 Pendiente |
| Exportación CSV/Excel | 🔲 Pendiente |
| Integración activa con Dataverse | 🔲 Pendiente |
