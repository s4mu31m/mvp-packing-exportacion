# Planificación y roadmap

> Referencia completa: [09 Planificación y roadmap — Wiki](https://github.com/s4mu31m/mvp-packing-exportacion/wiki/09-Planificacion-y-roadmap) · [09.1 Estado de Avance tras el Paso 3 — Wiki](https://github.com/s4mu31m/mvp-packing-exportacion/wiki/09.1-%C2%B7-Estado-de-Avance-tras-el-Paso-3)

---

## Estado de avance

| Bloque | Estado | Descripción |
|--------|--------|-------------|
| Paso 1 — Configuración del proyecto | ✅ Completado | Proyecto Django inicializado, estructura base definida |
| Paso 2 — Modelo de datos local en Django | ✅ Completado | Entidades Bin, Lote, Pallet, BinLote, PalletLote, RegistroEtapa implementadas con restricciones de unicidad y campos de auditoría |
| Paso 3 — Lógica de negocio por casos de uso | ✅ Completado | Capa de aplicación con 4 casos de uso implementados y validados con tests en verde |
| Paso 4 — Interfaz operativa mínima (REST + UI) | 🔲 Pendiente | Exposición de casos de uso vía endpoints, UI funcional tablet-first |
| Paso 5 — Integración con Dataverse | 🔲 Pendiente | Sincronización con Dataverse como base estructural de datos |

---

## Evidencia técnica del avance (Pasos 1–3)

```bash
python manage.py check      # sin errores
python manage.py test operaciones   # todos los tests en verde
```

**Tests cubren:**
- Alta de bin: registro correcto de un nuevo bin
- Rechazo de bin duplicado
- Creación de lote: flujo exitoso con bins válidos
- Rechazo por bins faltantes
- Cierre de pallet: flujo exitoso
- Flujo completo: bin → lote → pallet

---

## Brechas de implementación respecto del flujo completo

El flujo documentado contempla etapas aún no implementadas en el backend Django:

- Desverdizado (etapa vigente y no omitible)
- CamaraMantencion
- CalidadDesverdizado
- IngresoAPacking
- RegistroPacking / ControlProcesoPacking
- CalidadPallet
- CamaraFrio
- MedicionTemperaturaSalida

La integración activa con Dataverse también está pendiente de ejecutarse en ambiente real.

---

## Siguiente bloque recomendado — Paso 4

El paso siguiente natural es exponer la lógica operacional a través de una interfaz mínima.

### Alcance del Paso 4

- `POST /operaciones/bins/` → invoca `registrar_bin_recibido`
- `POST /operaciones/lotes/` → invoca `crear_lote_recepcion`
- `POST /operaciones/pallets/cerrar/` → invoca `cerrar_pallet`
- `POST /operaciones/eventos/` → invoca `registrar_evento_etapa`
- Implementar serializers de entrada y salida
- Traducir excepciones de dominio a respuestas HTTP apropiadas
- Tests de integración para los endpoints
- UI tablet-first funcional para recepción y consulta
- Consulta jefatura con filtros
- Exportación CSV/Excel

### Criterios de "done" para el Paso 4

- Los endpoints están implementados y accesibles en entorno local
- Cada endpoint invoca su caso de uso sin contener lógica de negocio propia
- Los errores de dominio se traducen a HTTP con códigos apropiados (400, 404, 409)
- Existe al menos un test de integración por endpoint (caso exitoso + caso de error)
- `python manage.py test operaciones` sigue en verde
- No hay lógica de negocio en las vistas

---

## Roadmap de referencia

### Semana 1 (16–20 mar 2026)
- Contrato bins e integridad
- Modelo relacional y ERD
- Staging y ETL base

### Semana 2 (23–27 mar 2026)
- Backend API de registro ← **Paso 3 completado en este bloque**
- UI tablet-first
- Upsert bins/lotes E2E

### Semana 3 (30 mar – 2 abr 2026)
- Trazabilidad bin → lote → etapas
- Consulta jefatura con filtros
- Exportación CSV/Excel

### Semana 4 (6–10 abr 2026)
- Piloto terreno y hardening
- Cierre, documentación y traspaso

---

## Ruta crítica

- Acceso al ambiente Dataverse del cliente (credenciales, tenant, Application User)
- Validación del modelo en Dataverse (tablas, columnas, relaciones)
- Interfaz tablet-first funcional y ágil para captura
- Incorporación de etapas pendientes al backend (Desverdizado, packing, cámaras)
- Exportación funcional

---

## Recomendación de secuencia

Completar el Paso 4 (interfaz operativa mínima) con tests de endpoints en verde **antes** de iniciar cualquier trabajo de integración con Dataverse. El campo `dataverse_id` nullable en las entidades maestras garantiza que esta decisión no requiere migraciones adicionales cuando llegue el momento.
