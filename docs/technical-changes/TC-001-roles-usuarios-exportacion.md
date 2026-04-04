# TC-001 — Roles, gestión de usuarios y exportación CSV

**Fecha:** 2026-03-30
**Rama:** `main`
**Issues impactadas:** OPER-003, UI-005
**Tipo de cambio:** Feature / Corrección de bug

---

## Contexto

El sistema carecía de:
- diferenciación de acceso por rol en portal y sidebar;
- vista de gestión de usuarios accesible desde la UI (sin depender de `/admin/`);
- exportación de datos operativos desde la vista de consulta jefatura;
- un helper de rol estable y centralizado para evitar permisos dispersos en templates.

Este cambio implementa el bloque mínimo para dejar el MVP operativo por rol.

---

## Archivos creados

### `python-app/src/usuarios/forms.py`

Formulario de creación de usuario con campo `rol` (Operador / Jefatura / Administrador).
El campo `rol` se mapea al momento del `save()`:

| Valor `rol` | `is_staff` | `is_superuser` |
|-------------|-----------|---------------|
| `operador`  | `False`   | `False`       |
| `jefatura`  | `True`    | `False`       |
| `administrador` | `True` | `True`      |

Usa `UserCreationForm` de Django como base para validación de contraseña.

### `python-app/src/usuarios/templates/usuarios/gestion_usuarios.html`

Vista de gestión de usuarios. Contiene:
- formulario de creación inline (no requiere página separada);
- tabla con username, nombre, correo, rol, estado activo/inactivo;
- botón de toggle activo/inactivo por usuario (excepto el propio usuario autenticado).

---

## Archivos modificados

### `python-app/src/usuarios/views.py`

**Añadido — Helpers de permisos (fuente única de verdad):**

```python
def es_administrador(user) -> bool   # is_active and is_superuser
def es_jefatura(user) -> bool        # is_active and (is_staff or is_superuser)
def es_operador(user) -> bool        # is_active
```

**Modificado — `PortalView._get_modulos(user)`:**
- recibe el objeto `user` como parámetro;
- muestra *Consulta Jefatura* solo si `es_jefatura(user)`;
- muestra *Gestión de Usuarios* solo si `es_administrador(user)`;
- *Producción Packing* visible para todos;
- *Frigorífico* como módulo futuro para todos.

**Añadido — `AdminRequiredMixin`:**
`UserPassesTestMixin` que delega a `es_administrador(user)`. Redirige a portal con mensaje si deniega.

**Añadidas — Nuevas vistas:**

| Vista | Método | Descripción |
|-------|--------|-------------|
| `GestionUsuariosView` | GET | Lista usuarios + formulario de creación |
| `CrearUsuarioView` | POST | Procesa `CaliProUserCreationForm`, redirige a listado |
| `ToggleUsuarioActivoView` | POST | Invierte `is_active` del usuario indicado por PK |

---

### `python-app/src/usuarios/urls.py`

Rutas añadidas bajo el prefijo `/usuarios/` (definido en `config/urls.py`):

| URL | View | `name` |
|-----|------|--------|
| `gestion/` | `GestionUsuariosView` | `gestion_usuarios` |
| `gestion/nuevo/` | `CrearUsuarioView` | `crear_usuario` |
| `gestion/<int:pk>/toggle/` | `ToggleUsuarioActivoView` | `toggle_usuario` |

Rutas absolutas resultantes:
- `/usuarios/gestion/`
- `/usuarios/gestion/nuevo/`
- `/usuarios/gestion/<pk>/toggle/`

---

### `python-app/src/usuarios/templates/usuarios/portal.html`

- Badge de rol visible junto al nombre de usuario (Administrador / Jefatura / Operador).
- Tarjetas de módulo filtradas por contexto `es_admin` y `es_jefatura` inyectados desde `PortalView`.
- Etiqueta de `rol_requerido` visible bajo el título de cada módulo restringido.
- Módulos no disponibles muestran "Próximamente" en lugar de botón deshabilitado sin contexto.

---

### `python-app/src/operaciones/views.py`

**Imports añadidos:** `csv`, `HttpResponse`, `UserPassesTestMixin`, `View`.

**Añadido — `_es_jefatura(user)`:**
Helper local equivalente al de `usuarios/views.py`; usado por los mixins de operaciones.

**Añadido — `JefaturaRequiredMixin`:**
`UserPassesTestMixin` que delega a `_es_jefatura(user)`. Redirige a portal si deniega.

**Añadido — `_lotes_enriquecidos_qs(temporada, filtro_productor, filtro_estado) -> list`:**

Extrae la lógica de construcción de lotes enriquecidos que antes estaba inline en `get_context_data`. Ahora es compartida entre `ConsultaJefaturaView` y `ExportarConsultaCSVView`.

Diferencias respecto a la implementación anterior:
- límite subido de 100 a 500 registros (suficiente para MVP, pendiente paginación);
- incluye campo `tipo_cultivo` (antes ausente);
- documentado con `TODO (Dataverse)` explícito en el punto de extensión.

**Modificado — `ConsultaJefaturaView`:**
- añade `JefaturaRequiredMixin` como base — la vista ahora es protegida por rol;
- `get_context_data` delegado a `_lotes_enriquecidos_qs`.

**Añadido — `ExportarConsultaCSVView`:**

```
GET /operaciones/consulta/exportar/?productor=...&estado=...
```

- Hereda `JefaturaRequiredMixin` — mismo control de acceso que la vista HTML.
- Acepta los mismos parámetros GET que `ConsultaJefaturaView`.
- Genera `Content-Type: text/csv; charset=utf-8` con BOM UTF-8 (`\ufeff`) para compatibilidad con Excel en Windows.
- Nombre de archivo: `lotes_<temporada>_<YYYYMMDD>.csv`.

Columnas del CSV:

| Encabezado | Campo fuente |
|------------|-------------|
| Temporada | `temporada` (inyectado) |
| Lote (code) | `lote_code` |
| Estado | `estado_display` |
| Etapa actual | `etapa` |
| Productor | `codigo_productor` del primer bin |
| Tipo cultivo | `tipo_cultivo` del primer bin |
| Variedad | `variedad_fruta` del primer bin |
| Bins | `cantidad_bins` |
| Kg neto | `kilos_neto_conformacion` |
| Fecha | `fecha_conformacion` o `created_at.date()` |

---

### `python-app/src/operaciones/web_urls.py`

Ruta añadida:

```python
path("consulta/exportar/", views.ExportarConsultaCSVView.as_view(), name="exportar_consulta"),
```

URL absoluta resultante: `/operaciones/consulta/exportar/`

---

### `python-app/src/operaciones/templates/operaciones/consulta.html`

Añadido `{% block page_actions %}` con enlace "Exportar CSV" que propaga los filtros activos como parámetros GET:

```
/operaciones/consulta/exportar/?productor=<valor>&estado=<valor>
```

Si no hay filtros activos el enlace apunta al endpoint sin query string (exporta todos los lotes de la temporada).

---

### `python-app/src/core/context_processors.py`

**`_nav_sections()` → `_nav_sections(user)`:**

La función ahora recibe el objeto `user` para construir el sidebar de forma diferenciada:

- **Todos los usuarios autenticados:** sección *Flujo Operativo* completa.
- **`is_staff` o `is_superuser`:** sección *Gestión* con *Consulta Jefatura*.
- **`is_superuser`:** además añade *Usuarios* (→ `/usuarios/gestion/`) en la sección *Gestión*.

Operadores sin `is_staff` no ven la sección Gestión en el sidebar.

---

### `python-app/src/templates/layout_app.html`

**Bug corregido:**
`request.user.perfil.rol_display` lanzaba `AttributeError` porque el modelo `Perfil` no existe en el proyecto. Reemplazado por:

```django
{% if request.user.is_superuser %}Administrador
{% elif request.user.is_staff %}Jefatura
{% else %}Operador
{% endif %}
```

---

## Modelo de roles

```
Condición Django       →  Rol visible en UI
─────────────────────────────────────────────
is_active (solo)       →  Operador
is_active + is_staff   →  Jefatura
is_active + is_superuser → Administrador
```

La lógica de decisión vive en:
- `usuarios/views.py` → `es_administrador()`, `es_jefatura()`, `es_operador()`
- `operaciones/views.py` → `_es_jefatura()` (equivalente local)

No hay permisos hardcodeados en templates fuera del portal.

---

## Compatibilidad Dataverse / SQLite

Los cambios de este TC son indiferentes al valor de `PERSISTENCE_BACKEND`:

- La gestión de usuarios opera exclusivamente sobre Django Auth local. No existe sincronización con Dataverse y no se implementó ninguna (no hay soporte en el repo).
- `_lotes_enriquecidos_qs` usa ORM local. El TODO documentado en el código marca el punto de extensión cuando `PERSISTENCE_BACKEND == 'dataverse'`.

No se rompió ningún flujo existente bajo ninguno de los dos backends.

---

## Rutas nuevas — resumen

| Método | URL | Acceso | Descripción |
|--------|-----|--------|-------------|
| GET | `/usuarios/gestion/` | Admin | Listado de usuarios + formulario |
| POST | `/usuarios/gestion/nuevo/` | Admin | Crear usuario |
| POST | `/usuarios/gestion/<pk>/toggle/` | Admin | Activar / desactivar usuario |
| GET | `/operaciones/consulta/exportar/` | Jefatura / Admin | Exportar CSV con filtros |

---

## Pendientes derivados (no en este TC)

| Item | Acción sugerida |
|------|----------------|
| Exportación Excel | Agregar `openpyxl` a `requirements.txt` e implementar `ExportarConsultaExcelView` reutilizando `_lotes_enriquecidos_qs` |
| `_lotes_enriquecidos_qs` para Dataverse | Implementar resolución OData cuando `PERSISTENCE_BACKEND == 'dataverse'` |
| Paginación en consulta jefatura | Actualmente limitado a 500 registros; implementar paginación antes de producción |
| Sincronización de usuarios con Dataverse | Solo si el modelo rector lo requiere; fuera del alcance de este MVP |
