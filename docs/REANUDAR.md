# Cómo retomar el proyecto

Estado al dejar el proyecto (2026-11-05). Todo lo de acá está commiteado: el
árbol de git está limpio y no hay nada a medias.

## 1. Qué falta, en una línea

**El despliegue en el VPS.** Todo lo demás está hecho y verificado.

## 2. Qué está hecho y verificado

| Parte | Cómo se verifica |
|-------|------------------|
| El parcial (capítulos 5 y 6) completo | `python scripts/e2e_check.py` → **TODO OK** (los casos C-01 a C-16) |
| Los casos de prueba a mano | `test/c-01..c-16*.http` + `test/solo_agregado.sql` |
| La evidencia de C-14 y C-15 | `evidencia/` |
| La imagen de Docker | `despliegue/Dockerfile` (base `python:3.12-alpine`, 74,7 MB) |
| Los casos D (D-01 a D-08) | `despliegue/evidencia/` — generados con `python scripts/capturar_d.py` |
| La guía para levantar todo | `MANUAL.md` |
| El zip de entrega | `python scripts/armar_zip.py "<Grupo>"` → `Parcial_Cap1a6_<Grupo>.zip` |

## 3. La consigna

Está en `C:\Users\Sabrina Gimenez\OneDrive\Documentos\Prog 3\Parcial_2_Consignas.docx`
(22 páginas: el parcial de Programación III, capítulos 1 a 6). Es la que
define los ejercicios 1 a 10, los casos C y D, y el formato de entrega.

## 4. El entorno de esta máquina

| Qué | Dónde / qué valor |
|-----|-------------------|
| Python | 3.13 en el sistema; el venv del proyecto en `.venv` (usar `.venv\Scripts\python.exe`) |
| PostgreSQL | 17.11 en `localhost:5432`; superusuario `postgres`, contraseña **`134679`** |
| Bases | `libreria` (el parcial) y `libreria_tp` (la copia del despliegue) |
| Docker | Docker Desktop 4.98.0 / motor 29.9.2, **funcionando** (WSL2 ya habilitado) |
| `.env` local | `postgresql+asyncpg://taller:taller@127.0.0.1:5432/libreria` (está en `.gitignore`) |

## 5. El VPS (lo único que falta)

| Dato | Estado |
|------|--------|
| Host | **177.7.32.86** |
| Puerto de SSH | 22 (acepta `publickey,password`) |
| Usuario | `root` (es el que usaste antes: está en tu `known_hosts` y en el historial) |
| Clave pública de esta máquina | `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMt5G8DpRdyiA/nFjj/N2XL40nvbHa2bxf6O29DEYwbL sabrina gimenez@DESKTOP-8EG30AO` — **la rechaza** (no está en el `authorized_keys` del root) |
| Puertos abiertos | 22 (ssh), 5432 (postgres), 80, 443, 3000. El **8000 está libre** |
| Contraseña de root | **FALTA** — hay que pedirla o agregar la clave de arriba |
| Puerto asignado por la cátedra | **FALTA** — si no lo hay, usar el 8000 |
| Datos de la base del VPS | **FALTAN** (usuario, contraseña, nombre). La base está en el mismo servidor (5432 abierto) |

### Cómo entrar (elegir una)

Con contraseña:

```bash
ssh root@177.7.32.86
```

Con clave (mejor, para no mandar la contraseña por chat) — en el VPS, como root:

```bash
mkdir -p ~/.ssh
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMt5G8DpRdyiA/nFjj/N2XL40nvbHa2bxf6O29DEYwbL sabrina gimenez@DESKTOP-8EG30AO' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Cómo desplegar

Opción A, el script (hace todo):

```bash
python scripts/desplegar.py 177.7.32.86 root 8000
```

Opción B, a mano (los comandos exactos están en `despliegue/DEPLOY.md`):

```bash
scp -r despliegue root@177.7.32.86:/root/libreria
ssh root@177.7.32.86
cd /root/libreria
nano libreria.env        # DATABASE_URL con los datos de la base del servidor
docker build -t libreria .
docker run -d --name libreria -p 8000:8000 --restart unless-stopped \
  --env-file libreria.env libreria
docker ps                # tiene que decir healthy
docker exec libreria python scripts/seed.py
python scripts/capturar_d.py   # la evidencia de D-01 a D-08, desde el servidor
```

### Después

1. Completar `despliegue/DEPLOY.md` con la **URL pública**, el **día y la hora**
   del despliegue y el **puerto** que se usó.
2. Dejar la evidencia definitiva de los casos D en `despliegue/evidencia/`.
3. Regenerar el zip: `python scripts/armar_zip.py "<Grupo>"`.

## 6. Los scripts

| Script | Qué hace |
|--------|----------|
| `scripts/seed.py` | Deja la base en el estado inicial conocido |
| `scripts/e2e_check.py` | Corre los casos C-01 a C-16 de punta a punta (llama al seed antes) |
| `scripts/capturar_c14.py` | Genera `evidencia/c-14-solo-agregado.txt` (el trigger de sólo agregado) |
| `scripts/capturar_c15.py` | Genera `evidencia/c-15-consultas-detalle.md` (consultas fijas del detalle de una venta) |
| `scripts/capturar_d.py` | Genera `despliegue/evidencia/d-01..d-08` |
| `scripts/desplegar.py` | Despliega en el VPS de punta a punta |
| `scripts/armar_zip.py` | Arma `Parcial_Cap1a6_<Grupo>.zip` |

## 7. Trampas que ya se pisaron (no repetirlas)

- **httpx manda el jar de cookies y descarta la cabecera `Cookie:` del pedido.**
  En el e2e, para probar dos sesiones a la vez hay que cambiar el jar antes de
  cada pedido (el helper `con_cookie`), no mandar la cabecera. Una cookie
  fijada a mano con `domain="testserver"` directamente no se envía: hay que
  fijarla **sin** dominio.
- **D-02 necesita una base vacía**: si la base ya está migrada, el log no
  muestra los `Running upgrade` y la evidencia queda floja.
- **D-08 necesita una venta del contenedor actual**: el aviso sale en el log
  del contenedor vivo, no del anterior (el caso D-04 lo recrea).
- **Dentro de un contenedor `localhost` es el propio contenedor**: la base del
  servidor se alcanza con `host.docker.internal` (en Linux, con
  `--add-host=host.docker.internal:host-gateway`).
- **El HEALTHCHECK va contra `127.0.0.1`**, no `localhost`: en Alpine
  `localhost` resuelve primero a `::1` y uvicorn escucha sólo en IPv4.
- **El `>>` de la consigna es un `<>`**: el CHECK de `movimiento_stock.cantidad`
  es `cantidad <> 0` y la cantidad va **con signo** (positiva entra, negativa
  sale). El stock de un libro es la suma de sus movimientos.
- **El id de una revisión de Alembic tiene que entrar en 32 caracteres**: es la
  columna `alembic_version.version_num`. `0003_acceso_y_movimientos` entra;
  `0003_acceso_movimientos_y_borrado_logico` no.
- **El `%` de la URL rompe la interpolación de configparser**: por eso
  `migrations/env.py` escapa el `%` al armar la URL.
- **El zip no puede llevar ningún `.env`**: `scripts/armar_zip.py` excluye
  todo archivo que termine en `.env` (incluido `despliegue/libreria.env`).
- **`asyncpg` en Windows decodifica el mensaje de error de PostgreSQL con la
  codificación de la consola**: el texto sale doblemente codificado. Para
  escribirlo bien hay que deshacerlo (`_reparar` en `scripts/capturar_c14.py`).

## 8. Decisiones de diseño que conviene no tocar

- `movimiento_stock.cantidad` es **con signo**; el stock es su suma.
- El ISBN es único **entre los vivos**: índice único parcial
  `WHERE borrado_en IS NULL`.
- `aplicar_movimiento_stock` (`app/modules/libros/service.py`) es el **único**
  punto donde se escribe el stock: lo usan el alta, la reposición y la venta.
- El módulo `despliegue/` es una **copia congelada** del TP de los capítulos 1
  a 4: no recibe los cambios del parcial (salvo el logger del aviso, anotado en
  su `DEPLOY.md`).
- El módulo `health` tiene **sólo `router.py`**, como pide la consigna.
- `Cliente.perfil` es uno a uno; `Cliente.usuario_id` es UNIQUE y nulo.
- `PerfilCliente` declara la unicidad como **restricción** (no como columna
  `unique`+`index`) para que el autogenerate no proponga cambios en una tabla
  del TP.
