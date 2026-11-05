# Plan de trabajo — Parcial Cap. 1 a 6 (Programación III)

Fuente: `Parcial_2_Consignas.docx` (Materia: Programación III).

## Estado (2026-11-05)

| Bloque | Estado |
|--------|--------|
| B0 · Congelar `despliegue/` | **Hecho** (copia del TP + Dockerfile + .dockerignore + env.example + DEPLOY.md + evidencia/) |
| B1 · Contenedor y VPS | **A medias**: la imagen se construye, el contenedor queda `healthy` y los casos D-01 a D-08 están verificados con evidencia. **Falta el VPS**: la URL pública y re-correr la evidencia desde el servidor |
| B2 · Configuración y ciclo de vida | **Hecho** (`Settings` con pydantic-settings, secretos sin default, pool y bcrypt en config) |
| B3 · Modelos y migraciones | **Hecho** (0003 autogenerada y leída, 0004 a mano con el trigger; `downgrade base` → `upgrade head` verificado) |
| B4 · Contratos y CRUD | **Hecho** (`extra="forbid"`, envoltorio de paginación, `DELETE /libros/{id}` → 204) |
| B5 · Autenticación | **Hecho** (bcrypt con semáforo, orden del login, hash ficticio, cookie HttpOnly) |
| B6 · Autorización | **Hecho** (roles vigentes en la base, autoprotección, dos grupos de rutas, `/mis-ventas`) |
| B7 · Repositorios y UoW | **Hecho** (dos jerarquías, precarga en el repositorio, un solo punto de escritura del stock) |
| B8 · Integridad | **Hecho** (disparador + `intento_acceso` en su propia transacción con su comentario) |
| B9 · Lecturas sin N+1 | **Hecho** (4 consultas fijas en el detalle de una venta, con 2 y con 4 renglones) |
| B10 · Datos, pruebas y entrega | **Hecho** (seed nuevo, casos C-01..C-16 en `.http` + `solo_agregado.sql`, evidencia de C-14 y C-15, README, script del zip) |

**Verificación**: `python scripts/e2e_check.py` → **TODO OK** (los casos C-01 a C-16).
`python scripts/capturar_d.py` → evidencia de D-01 a D-08 en `despliegue/evidencia/`.

**Pendiente de vos**:
1. Los datos del VPS: host, puerto de SSH, usuario de SSH, **puerto asignado
   por la cátedra para publicar la app**, y los datos de la base (host, puerto,
   usuario, contraseña y nombre de la base).
2. La base ya está: `libreria` (la del parcial) y `libreria_tp` (la del
   despliegue), con el superusuario `postgres` y la contraseña `134679`.

## Punto de partida

El repositorio actual **es el TP de los capítulos 1 a 4**, y está completo
(7 ejercicios del cuadernillo, entregables y verificación). El parcial pide
**dos carpetas nuevas** en el zip final:

```
Parcial_Cap1a6_<Grupo>.zip
├── parcial/     → TP cap. 1 a 4 + capítulos 5 y 6  (82 % de la nota)
└── despliegue/  → TP cap. 1 a 4 tal como se entregó + contenedor + VPS (18 %)
```

**Decisión clave:** `despliegue/` se congela con el código actual. A partir de
ahí el repo principal muta hacia `parcial/`. La copia del despliegue no recibe
los cambios del parcial (salvo defectos propios que impidan correr en
contenedor, que secorrigen y se anotan en `DEPLOY.md`).

## Bloques de trabajo

### B0 · Congelar `despliegue/` (copia del TP actual)

- [ ] Copiar el repo actual a `despliegue/` **antes** de tocar nada.
- [ ] **Defecto propio a corregir** (para que D-08 pase): el aviso del
      comprobante usa `logging.getLogger("libreria.ventas")`, un logger sin
      configurar → **no aparece** en el registro de uvicorn ni en
      `docker logs`. Pasar a `logging.getLogger("uvicorn.error")` y anotarlo
      en `DEPLOY.md`.

### B1 · Despliegue: imagen y VPS (Ej. 9 y 10 — 18 %)

- [ ] `Dockerfile` desde `python:3.12-alpine` (< 100 MB), con:
      `requirements.txt` primero y `pip install --no-cache-dir`; usuario sin
      privilegios + `USER`; sin secretos; CMD = `alembic upgrade head` y luego
      `uvicorn app.main:app --host 0.0.0.0 --port 8000`;
      `HEALTHCHECK` con `wget` contra **127.0.0.1** (no `localhost`: en Alpine
      `localhost` resuelve a `::1` y uvicorn escucha sólo IPv4).
- [ ] `.dockerignore` excluyendo `.env`, `.venv`, `.git`, `__pycache__`.
- [ ] `env.example` del contenedor (forma de `DATABASE_URL`, sin valores reales).
- [ ] `DEPLOY.md`: URL pública, día y hora, `docker build` y `docker run`
      completos (con el nombre del archivo de variables, sin su contenido),
      cambios hechos al TP, y cómo actualizar la aplicación.
- [ ] `evidencia/` con la salida de D-01 … D-08.
- [ ] Requisitos: **Docker no está instalado en esta máquina** (hay que
      instalarlo) y falta el acceso al VPS + base que provee la cátedra
      (host, puerto, usuario, contraseña, nombre de base, puerto asignado).

### B2 · Ej. 1 — Configuración y ciclo de vida (6 %)

- [ ] `app/core/config.py` → clase `Settings` con **pydantic-settings**.
- [ ] `DATABASE_URL` armado con `@computed_field` desde `POSTGRES_USER`,
      `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`
      + driver `postgresql+asyncpg`.
- [ ] `SECRET_KEY` (firma del token) y contraseña de BD **sin valor por
      defecto**: si faltan, la app no arranca.
- [ ] Coste de `bcrypt` declarado en la configuración (no fijo en el código).
- [ ] Tamaño del pool declarado en la configuración.
- [ ] `lifespan`: motor + fábrica en `app.state` (ya está) **+ hash ficticio
      del login calculado una vez al arrancar**.
- [ ] Ya está: `get_session` con `expire_on_commit=False`, `dispose()` al
      apagar, `/health/live` y `/health/ready` con 503.

### B3 · Ej. 2 — Modelos, relaciones y migraciones (10 %)

- [ ] `usuario`: id, email UNIQUE, nombre, password_hash, activo,
      debe_cambiar_password.
- [ ] `asignacion_rol`: id, usuario_id, rol, desde, vence_en (nulo),
      revocada_en (nulo), otorgada_por (nulo); CHECK de rol
      `IN ('ADMIN','VENDEDOR','CLIENTE')`; **índice único parcial**
      `(usuario_id, rol) WHERE revocada_en IS NULL`.
- [ ] `intento_acceso`: id, cuando, email, ip, exito; índice `(email, ip, cuando)`.
- [ ] `evento_seguridad`: id, cuando, actor (texto), accion.
- [ ] `cliente.usuario_id` (nulo, UNIQUE) + `Cliente.usuario` que devuelve un
      objeto, no una lista.
- [ ] `libro.borrado_en` (timestamptz, nulo); el ISBN deja de ser UNIQUE común
      y pasa a **índice único parcial** `WHERE borrado_en IS NULL`.
- [ ] `movimiento_stock`: id, libro_id, venta_id (nulo), usuario_id, cantidad
      (CHECK `> 0`), motivo, cuando — sólo agregado.
- [ ] Todas las FK nuevas con índice (PostgreSQL no los crea solo).
- [ ] Migración **0003 autogenerada** con todo lo anterior, **leída antes de
      aplicarla** y con un comentario que lo diga (si la versión generada tiene
      un problema, se corrige a mano y el comentario lo explica).
- [ ] Migración **0004 escrita a mano**: disparador append-only sobre
      `movimiento_stock` (la comparación automática no ve disparadores).
- [ ] `alembic upgrade head` sobre base vacía, `downgrade base`, `upgrade head`.

### B4 · Ej. 3 — Contratos y CRUD (8 %)

- [ ] `extra="forbid"` en todos los contratos de entrada (nadie se registra con
      un rol ni edita el stock por PATCH).
- [ ] Ninguna respuesta incluye `password_hash`.
- [ ] **Envoltorio de listados** `{items, total, page, size, pages}`: `page`
      desde 1, `size` 1..100 (default 20), página inexistente → 422, `total`
      con los mismos filtros que la página, cero resultados → una página vacía.
      Hoy todos los listados devuelven lista plana con `limit`/`offset`.
- [ ] `DELETE /libros/{id}` → **204** (borrado lógico).
- [ ] Ya está: `exclude_unset` en PATCH, 201/404/409/422, búsqueda con
      `ilike` ligado.

### B5 · Ej. 4 — Autenticación (14 %)

- [ ] `app/core/security.py`: hash con bcrypt (coste desde config, `to_thread`,
      **semáforo** que limita cuántas corrent a la vez), emisión y verificación
      del JWT (`sub`, `exp`, roles vigentes al emitir).
- [ ] Límite de **72 bytes** en todo campo que termina en bcrypt (son bytes, no
      caracteres: la «ñ» ocupa dos) → 422 y no 500.
- [ ] El hash se calcula **antes** de abrir la transacción.
- [ ] Orden del login: (1) límite de intentos → 429 con `Retry-After` **sin
      calcular ningún hash**; (2) verificación contra el hash real o contra un
      **hash ficticio** si el correo no existe (mismo mensaje y mismo tiempo).
- [ ] Token sólo en cookie `access_token`: `HttpOnly`, `SameSite=Lax`,
      `Max-Age` = duración del token, `Secure` configurable. Nunca en el cuerpo.
- [ ] Rutas: `POST /auth/registro` (RN-02: usuario + rol CLIENTE + cliente, o
      las tres filas o ninguna; 409 si ya existe cliente con ese correo),
      `POST /auth/login`, `POST /auth/logout` (borra la cookie),
      `GET /auth/yo`, `POST /auth/cambiar-password`.

### B6 · Ej. 5 — Autorización (12 %)

- [ ] `app/core/dependencies.py`: `get_usuario_actual` (401), roles vigentes,
      control del cambio obligatorio, `requiere_rol` (403).
- [ ] `requiere_rol` consulta `asignacion_rol` **en cada petición** (RN-04):
      revocar un rol quita el permiso a una sesión ya abierta.
- [ ] Rutas de personal: `POST /usuarios` (alta con contraseña provisoria),
      `GET /usuarios/{id}/roles`, `POST /usuarios/{id}/roles`,
      `DELETE /usuarios/{id}/roles/{rol}`, `GET /eventos`.
- [ ] RN-05 autoprotección: un admin no se revoca su propio ADMIN (409) y el
      sistema nunca queda sin administradores vigentes.
- [ ] Vencimiento con zona horaria **y** en el futuro; sin zona o en pasado → 422.
- [ ] Dos grupos de rutas en `main.py` (abierto / protegido con el control
      montado una sola vez).
- [ ] RN-14: `GET /mis-ventas` (sólo autenticado) + comprobación de dueño → 403.
- [ ] RN-16: `evento_seguridad` en la **misma** transacción; actor `SISTEMA`
      (texto) en la carga inicial.

### B7 · Ej. 6 — Repositorios y Unit of Work (16 %)

- [ ] `app/core/repository.py`: `BaseRepository[T]` (recibe **sesión y clase
      del modelo**; `get_by_id`, `get_all`, `count`, `add`, `update`, `delete`;
      `flush()` y **nunca** `commit()`) y `SoftDeleteRepository[T]` (filtra dados
      de baja; `get_by_id_including_deleted`, `soft_delete`).
- [ ] `app/core/unit_of_work.py`: gestor de contexto asincrónico; confirma al
      salir, revierte ante excepción, **no cierra la sesión** (no la creó).
- [ ] `app/core/paginacion.py`: envoltorio y cálculo de páginas.
- [ ] `repository.py` + `unit_of_work.py` en **cada módulo**; `health` sólo
      `router.py`.
- [ ] Precarga declarada **dentro del método del repositorio** que la necesita
      (hoy `joinedload`/`selectinload` viven en los services → hay que moverlos).
- [ ] El router construye el UoW con una dependencia; el servicio lo abre con
      `async with` y **nunca** lo construye.
- [ ] RN-02, RN-10 y RN-16 cada una en **un solo bloque**.
- [ ] Las dependencias de usuario actual y de rol reciben **la misma sesión**
      que el UoW (si no, cada petición autenticada toma dos conexiones del pool).
- [ ] RN-11: un **único punto de escritura de stock** (alta con stock inicial,
      reposición y venta).
- [ ] RN-10: la venta descuenta stock y deja un movimiento por renglón; si un
      libro no alcanza, no queda ninguna escritura (409).

### B8 · Ej. 7 — Integridad (10 %)

- [ ] Disparador append-only sobre `movimiento_stock` (migración 0004),
      rechaza UPDATE y DELETE venga de donde venga.
- [ ] `intento_acceso` se escribe desde **sesión y transacción propias, que se
      confirman siempre** (es la única escritura que no comparte la transacción
      de su petición). Con el comentario de las tres cosas: qué hace distinto,
      por qué no puede compartir la transacción y cuál es su costo.
- [ ] Los eventos de seguridad van en la misma transacción del cambio.

### B9 · Ej. 8 — Lecturas sin N+1 y asincronía (6 %)

- [ ] Detalle de venta con **número fijo** de consultas, incluso con libros
      dados de baja.
- [ ] Ninguna lectura depende de carga perezosa.
- [ ] Todos los handlers `async def` y ninguna llamada bloqueante.
- [ ] El aviso del comprobante con `BackgroundTasks` debe **verse en el
      registro de uvicorn** (arreglar el logger — mismo fix que B0).

### B10 · Datos, pruebas y entrega

- [ ] `seed.py` del parcial: 5 usuarios (admin, admin2, vendedor, ana,
      nuevo — este último con cambio obligatorio), 3 editoriales, 3 géneros,
      6 autores, 5 libros con su stock, 3 clientes (Lucía con perfil, Tomás sin
      usuario, Ana Paz con usuario), la venta 1 (Rayuela ×1 + Ficciones ×2 =
      69000.00), movimientos de stock que cuadren con el stock de los 5 libros,
      y una línea de `evento_seguridad` con actor `SISTEMA`.
- [ ] `test/`: casos **C-01 … C-16** en `.http` (hoy hay C-01 … C-08 del TP) y
      `test/solo_agregado.sql` para el caso C-14.
- [ ] `evidencia/` en `parcial/`: C-15 (consultas de una venta con 2 y con 4
      renglones) y C-14 (captura de psql).
- [ ] `README.md` con nombres y apellidos de los integrantes y los pasos para
      levantarlo desde cero: venv, dependencias, `.env` (incluido **cómo
      generar la clave de firma**), `alembic upgrade head`, `python seed.py`,
      arranque del servidor.
- [ ] `requirements.txt`: agregar `pydantic-settings`, `bcrypt`, `PyJWT`.
- [ ] Zip final `Parcial_Cap1a6_<Grupo>.zip` con `parcial/` y `despliegue/`,
      **sin** `.venv`, `__pycache__` ni `.env`, y **sin credenciales reales**
      (tampoco en el historial de `.git` si se incluye).

## Orden sugerido

1. **B0** (congelar despliegue) — 5 min, y bloquea todo lo demás.
2. **B2 + B3** (config + modelos + migraciones) — base de todo lo demás.
3. **B7** (repositorios + UoW) — refactor estructural, más invasivo.
4. **B5 + B6** (auth + autorización) — el grueso de la nota (26 %).
5. **B4** (contratos/CRUD/paginación) — se puede en paralelo con 4.
6. **B8** (trigger + intento_acceso) — cierre de migraciones.
7. **B9** (N+1 + asincronía) — barrido final.
8. **B10** (seed, pruebas, README, zip).
9. **B1** (contenedor + VPS) — depende de Docker instalado y del VPS; se
   puede arrancar en paralelo desde B0, pero el despliegue usa el código
   congelado, así que **no depende** de los bloques 2-8.
