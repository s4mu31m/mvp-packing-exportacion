# Autenticación, Usuarios y Permisos — Diseño técnico

> Implementado: 2026-04-01
> Backend: Python + Django 6 + SQLite / Microsoft Dataverse Web API OData v4

---

## Decisión técnica adoptada

**No se usó custom `AUTH_USER_MODEL`.**
Se optó por mantener el `User` de Django nativo como capa de sesión liviana y agregar una capa de usuarios operativos propia (`UsuarioProfile` en SQLite, `crf21_usuariooperativos` en Dataverse).

Motivo: reemplazar `AUTH_USER_MODEL` requiere migración destructiva y rompe el estado actual del proyecto. La solución adoptada es compatible con `LoginRequiredMixin`, sesiones y todo el middleware existente.

---

## Arquitectura de usuarios

```
crf21_usuariooperativos  (Dataverse)
       ↕  (misma interfaz)
UsuarioProfile           (SQLite — espejo local del esquema Dataverse)
       ↕
UsuarioRepository        (interfaz ABC)
       ├── SQLiteUsuarioRepository    → UsuarioProfile ORM
       └── DataverseUsuarioRepository → OData v4
       ↕
CaliProAuthBackend       (AUTHENTICATION_BACKENDS)
       ↕
Django User              (solo para sesión / middleware)
       ↕
Session: crf21_rol, crf21_codigooperador, ...
       ↕
usuarios/permissions.py  (fuente única de verdad de permisos)
```

---

## Contrato de campos — crf21_usuariooperativos

| Campo dominio    | Campo Dataverse              | Tipo    | Notas                                 |
|------------------|------------------------------|---------|---------------------------------------|
| `id`             | `crf21_usuariooperativoid`   | UUID    | PK                                    |
| `usernamelogin`  | `crf21_usernamelogin`        | string  | Identificador de login, único         |
| `nombrecompleto` | `crf21_nombrecompleto`       | string  |                                       |
| `correo`         | `crf21_correo`               | string  |                                       |
| `passwordhash`   | `crf21_passwordhash`         | string  | Hash Django (PBKDF2). Compatible con `check_password()` |
| `rol`            | `crf21_rol`                  | string  | Texto separado por coma. Ej: `"Recepcion, Pesaje"` |
| `activo`         | `crf21_activo`               | bool    | False = no puede entrar               |
| `bloqueado`      | `crf21_bloqueado`            | bool    | True = no puede entrar                |
| `codigooperador` | `crf21_codigooperador`       | string  | Generado en backend. Inmutable.       |

---

## Estrategia SQLite vs Dataverse

| Aspecto              | SQLite                                    | Dataverse                                     |
|----------------------|-------------------------------------------|-----------------------------------------------|
| Modelo               | `UsuarioProfile` (ORM Django)             | `crf21_usuariooperativos` (OData v4)          |
| Autenticación        | `SQLiteUsuarioRepository.get_by_username` | `DataverseUsuarioRepository.get_by_username`  |
| Creación usuario     | ORM + `UsuarioProfile.objects.create`     | `DataverseClient.create_row`                  |
| Toggle activo        | ORM `update_fields=["activo"]`            | `DataverseClient.update_row`                  |
| Listado              | `UsuarioProfile.objects.all()`            | `client.list_rows(crf21_usuariooperativos)`   |
| Selector             | `PERSISTENCE_BACKEND=sqlite` (default)    | `PERSISTENCE_BACKEND=dataverse`               |

En ambos modos, la interfaz consumida por vistas y auth backend es idéntica (`UsuarioRepository`).

---

## Convención de crf21_codigooperador

Generado al crear el usuario. **Nunca modificable** (ignorado en `update()`).

| Rol primario   | Prefijo | Ejemplo   |
|----------------|---------|-----------|
| Administrador  | `ADM`   | `ADM-001` |
| Jefatura       | `JEF`   | `JEF-001` |
| Cualquier otro | `OPE`   | `OPE-001` |

El sufijo es un contador zero-padded a 3 dígitos por prefijo. No es global — cada prefijo tiene su propio secuencial.

---

## Flujo de autenticación

1. Usuario envía username + password al login form.
2. Django llama a `CaliProAuthBackend.authenticate()` (primer backend en `AUTHENTICATION_BACKENDS`).
3. El backend consulta `UsuarioRepository.get_by_username(username)`.
4. Verifica contraseña con `check_password(password, perfil.passwordhash)`.
5. Rechaza si `activo=False` o `bloqueado=True`.
6. Obtiene o crea un `Django User` (solo para sesión). Sincroniza `is_staff`/`is_superuser` desde `crf21_rol`.
7. `CaliProLoginView.form_valid()` llama `store_user_session()` → guarda `crf21_rol`, `crf21_codigooperador`, etc. en sesión.
8. Todas las verificaciones de permisos posteriores leen desde `request.session["crf21_rol"]`.

**Fallback:** Si `CaliProAuthBackend` retorna `None`, Django prueba `ModelBackend`. Esto permite que superusuarios creados con `createsuperuser` sigan funcionando.

---

## Matriz de permisos por módulo

| Módulo / Vista           | Rol requerido              | Mixin / Helper                      |
|--------------------------|----------------------------|-------------------------------------|
| Portal / Dashboard       | Cualquier autenticado      | `LoginRequiredMixin`                |
| Dashboard operativo      | Cualquier autenticado      | `LoginRequiredMixin`                |
| Recepcion                | Recepcion                  | `RolRequiredMixin`                  |
| Conformar Lote (Pesaje)  | Pesaje                     | `RolRequiredMixin`                  |
| Desverdizado             | Desverdizado               | `RolRequiredMixin`                  |
| Ingreso Packing          | Ingreso Packing            | `RolRequiredMixin`                  |
| Proceso Packing          | Proceso                    | `RolRequiredMixin`                  |
| Control Proceso          | Control                    | `RolRequiredMixin`                  |
| Paletizado               | Paletizado                 | `RolRequiredMixin`                  |
| Camaras Frio             | Camaras                    | `RolRequiredMixin`                  |
| Consulta Jefatura        | Jefatura, Administrador    | `JefaturaRequiredMixin`             |
| Exportar CSV             | Jefatura, Administrador    | `JefaturaRequiredMixin`             |
| Gestión de Usuarios      | Administrador              | `AdminRequiredMixin`                |

La matriz completa está definida en `MODULO_ROL_MAP` dentro de `usuarios/permissions.py`.

> **Administrador bypasea todos los checks de rol** (`is_admin()` se evalúa primero en `RolRequiredMixin.test_func()`).
> **Acceso denegado** redirige a `LOGIN_URL` vía `UserPassesTestMixin`.

### Roles operativos disponibles

```
Recepcion | Pesaje | Desverdizado | Ingreso Packing | Proceso
Control | Paletizado | Camaras | Jefatura | Administrador
```

Los roles se almacenan en `crf21_rol` como string canónico separado por coma con espacio: `"Recepcion, Pesaje"`.

---

## Módulo de permisos central — usuarios/permissions.py

Todas las verificaciones de acceso deben pasar por este módulo. No duplicar lógica en templates ni views.

```python
from usuarios.permissions import (
    get_roles,          # → list[str] desde sesión
    is_admin,           # → bool: tiene rol Administrador
    is_jefatura,        # → bool: tiene rol Jefatura o Administrador
    has_role,           # → bool: tiene al menos uno de los roles dados (o es Admin)
    puede_acceder_modulo,  # → bool: verifica MODULO_ROL_MAP
)
```

---

## Cómo probar en SQLite

```bash
# 1. Migrar
PERSISTENCE_BACKEND=sqlite python manage.py migrate

# 2. Crear usuario administrador
# Desde la UI de gestión de usuarios (requiere superuser Django nativo):
python manage.py createsuperuser  # usuario de bootstrap

# 3. Crear usuarios operativos desde la UI /usuarios/gestion/

# 4. Ejecutar tests
python manage.py test usuarios.test.test_usuarios -v 2
```

El usuario creado con `createsuperuser` se autentica vía `ModelBackend` (fallback).
Para usar el nuevo sistema, crear usuarios desde `/usuarios/gestion/`.

---

## Cómo probar en Dataverse

Requisitos en `.env`:
```
PERSISTENCE_BACKEND=dataverse
DATAVERSE_URL=https://org...crm2.dynamics.com
DATAVERSE_TENANT_ID=...
DATAVERSE_CLIENT_ID=...
DATAVERSE_CLIENT_SECRET=...
```

Verificación manual:
1. Acceder a `/api/dataverse/check_tables/` → verificar que `crf21_usuariooperativos` es accesible.
2. Crear un usuario en Dataverse con los campos requeridos (o desde la UI `/usuarios/gestion/`).
3. Verificar que `crf21_passwordhash` contiene un hash Django (`pbkdf2_sha256$...`).
4. Login con ese usuario → debe llegar al portal con roles desde `crf21_rol`.
5. Cambiar `crf21_activo=false` en Dataverse → login debe ser rechazado.
6. Cambiar `crf21_bloqueado=true` → login rechazado.
7. Crear usuario con multiselect de roles → verificar `crf21_rol` en Dataverse como string separado por coma.

---

## Archivos creados / modificados

### Nuevos
| Archivo | Descripción |
|---------|-------------|
| `usuarios/permissions.py` | Módulo central de permisos por rol |
| `usuarios/auth_backend.py` | `CaliProAuthBackend` + `store_user_session` |
| `usuarios/models.py` | `UsuarioProfile` (SQLite mirror de crf21_usuariooperativos) |
| `usuarios/migrations/0001_initial.py` | Migración de UsuarioProfile |
| `usuarios/repositories/__init__.py` | `UsuarioRecord` + `UsuarioRepository` (ABC) + factory |
| `usuarios/repositories/sqlite_repo.py` | Implementación SQLite |
| `usuarios/repositories/dataverse_repo.py` | Implementación Dataverse |
| `usuarios/test/test_usuarios.py` | 43 tests automatizados |

### Modificados
| Archivo | Cambio |
|---------|--------|
| `usuarios/views.py` | Usa `UsuarioRepository` y `permissions.py`. Agrega `RolRequiredMixin`. |
| `usuarios/forms.py` | `UsuarioCreacionForm` con multiselect de roles alineado a Dataverse |
| `usuarios/urls.py` | `<str:pk>` para soportar UUID Dataverse en toggle |
| `usuarios/templates/usuarios/gestion_usuarios.html` | Multiselect roles, columna codigooperador, datos de UsuarioRecord |
| `core/context_processors.py` | Sidebar filtrado por `puede_acceder_modulo(request, modulo)` — ítems operativos solo visibles si el usuario tiene el rol correspondiente |
| `operaciones/views.py` | `RolRequiredMixin` local (importa `get_roles`/`is_admin` de `usuarios.permissions`); aplicado a las 8 vistas operativas. `JefaturaRequiredMixin` usa `is_jefatura(request)` |
| `config/settings/base.py` | `AUTHENTICATION_BACKENDS` con `CaliProAuthBackend` + `ModelBackend` |
| `infrastructure/dataverse/mapping.py` | Agrega `ENTITY_SET_USUARIO_OPERATIVO` y `USUARIO_OPERATIVO_FIELDS` |

---

## Límites conocidos y brechas pendientes

1. **Generación de codigooperador no atómica en Dataverse**: Usa `count()` de registros existentes. Bajo carga concurrente alta podría haber duplicados. Aceptable para escala MVP; se puede mejorar con un campo contador en Dataverse.

2. **Cambio de contraseña**: No implementado en UI. El hash se establece al crear el usuario y no hay vista de edición de contraseña.

3. **Sin token de reset de contraseña**: Flujo de recuperación de contraseña no implementado.

4. **Sincronización Django User ↔ UsuarioProfile**: Cambios en Dataverse no se reflejan en `auth_user` hasta el próximo login (el backend sincroniza en cada autenticación exitosa).

5. **Tests Dataverse**: Solo validación manual documentada; los tests automáticos usan `@override_settings(PERSISTENCE_BACKEND="sqlite")`.
