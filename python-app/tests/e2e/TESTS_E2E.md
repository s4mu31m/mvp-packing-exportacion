# Suite de Tests E2E — CaliPro Packing Exportación

## ¿Qué son estos tests?

Son **automatizaciones reales de navegador** (equivalente a Cypress) implementadas con
[Playwright for Python](https://playwright.dev/python/). Cada test abre un navegador
Chromium, navega por la aplicación, hace clic en botones, llena formularios y lee
mensajes en pantalla — exactamente igual que lo haría un operador humano.

No se hace ningún bypass de la UI: todo el tráfico pasa por el servidor Django real
levantado en un puerto local (`live_server`), incluyendo autenticación, CSRF, sesiones,
validaciones HTML5 y lógica de negocio.

---

## Resultados — última ejecución (2026-04-07)

```
86 tests  ·  0 fallos  ·  0 skip  ·  ~3 min 7 seg
Navegador: Chromium (headless)
```

| Archivo | Tests | Resultado |
|---------|------:|-----------|
| `test_auth.py` | 15 | ✅ todos pasan |
| `test_consulta.py` | 10 | ✅ todos pasan |
| `test_form_validation.py` | 7 | ✅ todos pasan |
| `test_rbac.py` | 20 | ✅ todos pasan |
| `test_recepcion.py` | 10 | ✅ todos pasan |
| `test_ui_interactions.py` | 7 | ✅ todos pasan |
| `test_user_management.py` | 10 | ✅ todos pasan |
| `test_workflow_mvp.py` | 5 | ✅ todos pasan |
| **TOTAL** | **86** | **✅ 86/86** |

---

## Cómo ejecutarlos

### Headless (CI / rápido)
```bash
cd python-app
python -m pytest tests/e2e/ -v
```

### Con navegador visible (modo Cypress — ver qué hace el bot)
```bash
python -m pytest tests/e2e/ -v --headed --slowmo=500
```
`--slowmo=500` agrega 500 ms entre acciones para seguirlo visualmente.

### Un test específico
```bash
python -m pytest tests/e2e/test_recepcion.py::test_cerrar_lote_after_adding_bin -v --headed
```

### Primera vez (instalación)
```bash
pip install -r requirements-dev.txt
playwright install chromium
```

---

## Arquitectura

### Page Object Model (POM)

Cada módulo de la UI tiene su propia clase que encapsula los selectores y acciones:

```
tests/e2e/
├── conftest.py               # Fixtures compartidos: make_user, login, as_admin…
├── pages/
│   ├── login_page.py
│   ├── portal_page.py
│   ├── dashboard_page.py
│   ├── recepcion_page.py
│   ├── consulta_page.py
│   ├── gestion_usuarios_page.py
│   ├── control_page.py
│   ├── desverdizado_page.py
│   ├── ingreso_packing_page.py
│   ├── proceso_page.py
│   ├── paletizado_page.py
│   └── camaras_page.py
├── test_auth.py
├── test_rbac.py
├── test_recepcion.py
├── test_consulta.py
├── test_user_management.py
├── test_form_validation.py
├── test_ui_interactions.py
└── test_workflow_mvp.py
```

### Fixtures principales (`conftest.py`)

| Fixture | Qué hace |
|---------|----------|
| `make_user` | Crea un `UsuarioProfile` con rol y contraseña hasheada en la BD de test |
| `login` | Abre `/usuarios/login/`, llena usuario+contraseña y hace clic en "Acceder" |
| `as_admin` | Página ya autenticada como `Administrador` |
| `as_recepcion` | Página ya autenticada como operador de `Recepcion` |
| `as_jefatura` | Página ya autenticada como `Jefatura` |
| `as_control` | Página ya autenticada como `Control` |

### Infraestructura técnica

- **Backend**: `PERSISTENCE_BACKEND=sqlite` forzado en tiempo de prueba (el `.env` de
  producción puede tener `dataverse`; los tests siempre usan SQLite local).
- **Base de datos**: `transactional_db` — los datos se persisten realmente entre
  fixture y test (necesario para que el servidor Django los vea desde otro hilo),
  y se truncan automáticamente después de cada test.
- **Async safety**: `DJANGO_ALLOW_ASYNC_UNSAFE=true` para compatibilidad con el event
  loop interno de Playwright en Django 6.0.

---

## Detalle por módulo

---

### `test_auth.py` — Autenticación (15 tests)

Verifica el ciclo completo de login/logout y la protección de rutas sin sesión.

| Test | Flujo en el navegador |
|------|-----------------------|
| `test_login_success_redirects_to_portal` | Abre `/login/`, escribe usuario y contraseña válidos, hace clic en "Acceder" → verifica redirect a `/portal/` |
| `test_login_wrong_password_shows_error` | Introduce contraseña incorrecta → verifica que aparezca mensaje de error en pantalla |
| `test_login_wrong_username_shows_error` | Usuario que no existe → verifica mensaje de error |
| `test_login_inactive_user_rejected` | Usuario con `activo=False` → el login es rechazado |
| `test_login_blocked_user_rejected` | Usuario con `bloqueado=True` → el login es rechazado |
| `test_logout_redirects_to_login` | Hace clic en "Cerrar sesión" → verifica redirect a `/login/` |
| `test_login_page_has_csrf_token` | Inspecciona el DOM: el formulario debe tener `csrfmiddlewaretoken` |
| `test_unauthenticated_access_redirects_to_login` × 8 | Visita cada ruta protegida sin sesión → verifica redirect a `/login/` (rutas: `/operaciones/`, recepcion, desverdizado, ingreso-packing, proceso, control, paletizado, camaras) |

---

### `test_rbac.py` — Control de acceso por rol (20 tests)

Verifica que cada rol solo pueda acceder a sus módulos y que el portal muestre el badge correcto.

| Test | Flujo en el navegador |
|------|-----------------------|
| `test_admin_badge_in_portal` | Login como Administrador → verifica badge "Administrador" en el portal |
| `test_jefatura_badge_in_portal` | Login como Jefatura → verifica badge "Jefatura" |
| `test_operador_badge_in_portal` | Login como operador → verifica badge "Operador" |
| `test_role_can_access_own_module` × 7 | Cada rol (Recepcion, Desverdizado, Ingreso Packing, Proceso, Control, Paletizado, Camaras) puede acceder a su URL correspondiente sin ser rechazado |
| `test_jefatura_can_access_consulta` | Jefatura puede acceder a `/operaciones/consulta/` |
| `test_recepcion_cannot_access_consulta` | Operador de Recepcion es redirigido al intentar acceder a Consulta |
| `test_admin_can_access_all_routes` × 9 | Administrador accede sin restricción a todas las rutas: recepcion, desverdizado, ingreso-packing, proceso, control, paletizado, camaras, consulta, gestión usuarios |
| `test_non_admin_cannot_access_gestion_usuarios` | Un Jefatura es rechazado en `/usuarios/gestion/` |

---

### `test_recepcion.py` — Flujo de recepción de bins (10 tests)

Automatiza el módulo principal de recepción end-to-end.

| Test | Flujo en el navegador |
|------|-----------------------|
| `test_recepcion_page_loads_with_iniciar_form` | Navega a recepción → verifica que el formulario "Iniciar Lote" está visible |
| `test_iniciar_lote_creates_active_state` | Hace clic en "Iniciar Lote" → verifica que aparece el formulario de bins |
| `test_iniciar_lote_shows_badge_with_lote_code` | Inicia lote → verifica que el header muestra el badge con el código `LP-AAAA-BBBB-NNNNNN` |
| `test_add_first_bin_shows_success_message` | Llena código productor, variedad, color y peso → hace clic en "Agregar Bin" → verifica mensaje de éxito |
| `test_add_bin_appears_in_sidebar` | Agrega un bin → verifica que aparece en el panel lateral de bins |
| `test_base_fields_become_readonly_after_first_bin` | Agrega un bin → verifica que los campos base (productor, variedad, color) quedan en `readonly` |
| `test_scanner_simulation_available` | Verifica que `window.simularScan()` está disponible en el contexto JS de la página |
| `test_cerrar_lote_button_disabled_with_zero_bins` | Inicia lote sin agregar bins → verifica que el botón "Cerrar Lote" está deshabilitado |
| `test_cerrar_lote_after_adding_bin` | Agrega bin → llena kilos bruto/neto → hace clic en "Cerrar Lote" → verifica éxito |
| `test_cerrar_lote_returns_to_iniciar_form` | Cierra lote → verifica que la página vuelve al estado inicial (sin lote activo) |

---

### `test_consulta.py` — Consulta Jefatura (10 tests)

Verifica la vista de consulta de lotes, filtros y exportación CSV.

| Test | Flujo en el navegador |
|------|-----------------------|
| `test_consulta_loads_for_jefatura` | Login como Jefatura → navega a `/operaciones/consulta/` → verifica título de página |
| `test_consulta_blocked_for_recepcion` | Login como Recepcion → intenta acceder a consulta → es redirigido |
| `test_consulta_empty_state_with_no_lotes` | Admin sin lotes creados → consulta muestra estado vacío |
| `test_consulta_shows_lote_after_creation` | Crea y cierra un lote desde recepción → va a consulta → el lote aparece en la tabla |
| `test_filter_by_productor_shows_matching_lotes` | Llena el filtro de productor → verifica que solo aparecen lotes de ese productor |
| `test_filter_by_productor_no_match_shows_empty` | Filtra por productor inexistente → tabla muestra estado vacío |
| `test_filter_by_estado_cerrado` | Filtra por estado "cerrado" → solo aparecen lotes cerrados |
| `test_clear_filter_resets_results` | Aplica filtro → hace clic en limpiar → todos los lotes vuelven a aparecer |
| `test_export_csv_returns_download` | Hace clic en "Exportar CSV" → verifica que se descarga un archivo |
| `test_export_csv_with_filter` | Aplica filtro y exporta → verifica descarga |

---

### `test_user_management.py` — Gestión de usuarios (10 tests)

Automatiza la creación, validación y toggling de usuarios desde la UI de administración.

| Test | Flujo en el navegador |
|------|-----------------------|
| `test_gestion_page_loads_for_admin` | Admin navega a `/usuarios/gestion/` → la página carga correctamente |
| `test_gestion_blocked_for_jefatura` | Jefatura intenta acceder a gestión → es rechazado |
| `test_create_user_with_single_role` | Llena el form con username, contraseña y un solo rol → crea usuario → verifica en la tabla |
| `test_create_user_with_multiple_roles` | Crea usuario con roles Recepcion + Control → verifica en la tabla |
| `test_create_admin_user` | Crea usuario con rol Administrador → verifica en la tabla |
| `test_created_user_can_login` | Crea usuario desde la UI → abre sesión limpia (sin cookies) → hace login con ese usuario → verifica acceso al portal |
| `test_create_user_password_mismatch_shows_error` | Contraseñas distintas → hace clic en Crear → verifica mensaje de error |
| `test_create_duplicate_username_shows_error` | Intenta crear usuario con nombre ya existente → verifica error |
| `test_toggle_user_inactive` | Crea usuario activo → hace clic en "Desactivar" → verifica que la tabla muestra "No" en columna Activo |
| `test_cannot_toggle_self` | El admin no puede desactivarse a sí mismo → verifica que su propia fila no tiene botón de toggle |

---

### `test_form_validation.py` — Validaciones de formularios (7 tests)

Verifica que los formularios rechacen datos incorrectos o incompletos.

| Test | Flujo en el navegador |
|------|-----------------------|
| `test_bin_form_required_codigo_productor` | Inicia lote → envía el formulario de bin sin código de productor → verifica que no se agrega ningún bin (validación HTML5 bloquea el envío) |
| `test_bin_form_required_variedad` | Envía bin sin variedad → 0 bins agregados |
| `test_bin_form_required_color` | Envía bin sin color → 0 bins agregados |
| `test_cerrar_lote_button_disabled_without_bins` | Inicia lote → verifica que "Cerrar Lote" está `disabled` con 0 bins |
| `test_create_user_password_mismatch` | Contraseñas distintas en el form de creación → verifica `.alert-danger` |
| `test_create_user_missing_username` | Sin username → validación HTML5 impide el envío → la URL no cambia |
| `test_create_user_no_roles_selected` | Sin roles seleccionados → verifica error del servidor |

---

### `test_ui_interactions.py` — Interacciones de UI (7 tests)

Verifica comportamientos de JavaScript: escáner, toasts, reloj y sidebar.

| Test | Flujo en el navegador |
|------|-----------------------|
| `test_simular_scan_function_exists` | Navega a recepción con lote activo → evalúa `typeof window.simularScan` → debe ser `"function"` |
| `test_simular_scan_calls_process_scan` | Llama a `window.simularScan("BIN-TEST-001")` desde el contexto JS → no debe lanzar excepciones |
| `test_toast_appears_after_iniciar_lote` | Inicia lote → el mensaje de éxito del servidor se muestra en pantalla |
| `test_toast_appears_after_agregar_bin` | Agrega bin → verifica que aparece `.alert-success` |
| `test_live_clock_present_in_app_layout` | Visita el dashboard → el elemento `#live-time` existe y tiene contenido (hora actual) |
| `test_sidebar_highlights_current_page` | Navega a recepción → verifica que al menos un ítem del sidebar tiene clase `active` |
| `test_all_forms_have_csrf_token` | Inspecciona todos los `<form>` en recepción → cada uno tiene `csrfmiddlewaretoken` |

---

### `test_workflow_mvp.py` — Pipeline MVP completo (5 tests)

Flujos integrados de punta a punta que cruzan múltiples vistas.

| Test | Flujo en el navegador |
|------|-----------------------|
| `test_dashboard_loads_for_authenticated_user` | Login como admin → navega al dashboard → verifica que carga |
| `test_dashboard_shows_empty_state_with_no_lotes` | BD vacía → dashboard muestra empty state |
| `test_reception_creates_lote_visible_in_dashboard` | Completa una recepción entera (iniciar → bin → cerrar) → va al dashboard → el lote aparece en la tabla |
| `test_dashboard_ver_todos_goes_to_consulta` | Crea lote → dashboard → hace clic en "Ver todos →" → aterriza en `/consulta/` |
| `test_full_reception_pipeline` | **Pipeline completo**: login → verificar form inicial → iniciar lote → verificar badge → agregar bin → verificar mensaje → cerrar lote → verificar vuelta al estado inicial |

---

## Notas técnicas importantes

### Por qué no se usa `cy.request()` ni el cliente de Django

Todos los tests pasan por el navegador real. La autenticación ocurre a través del
formulario de login (no por `force: true` de Cypress ni `client.force_login()`), lo que
garantiza que el pipeline completo de Django — `CaliProAuthBackend`, `store_user_session()`,
`crf21_rol`, `crf21_codigooperador` — se ejecuta igual que en producción.

### Aislamiento de datos

Cada test recibe una base de datos limpia gracias a `transactional_db`. Los datos
creados en un test nunca contaminan el siguiente.

### Compatibilidad con `.env` de producción

Aunque el `.env` tenga `PERSISTENCE_BACKEND=dataverse`, los tests E2E siempre usan
SQLite local. El `conftest.py` fuerza esto directamente sobre el objeto vivo de
settings de Django antes de que se cree cualquier fixture.

### Selector strategy

Los tests usan la jerarquía recomendada por Playwright:
1. `get_by_label()` / `get_by_role()` — semánticos, resistentes a cambios de CSS
2. `get_by_text()` — para mensajes y títulos
3. `locator("#id")` / `locator(".clase")` — solo cuando los anteriores no aplican
4. `locator('label:has([name="roles"])')` — para inputs ocultos por CSS (role-chip)
