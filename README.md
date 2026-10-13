# Sofre Digital Python Test

App de prueba para validar el deploy automático de proyectos **Python (FastAPI) + PostgreSQL**.

Muestra un dashboard con info del deploy (versión, commit, host/contenedor, uptime), el estado de la conexión a Postgres, un contador de visitas y un muro de mensajes persistidos en la base. Es el equivalente en Python de `test-node`, con los mismos endpoints y variables.

## Stack

- Python 3.13 / FastAPI + Uvicorn
- PostgreSQL (driver `psycopg` 3 con pool async)
- Frontend estático (HTML + CSS + JS, sin build) servido por la misma app

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `PORT` | `8000` | Puerto HTTP |
| `DATABASE_URL` | — | URL de conexión (`postgres://user:pass@host:5432/db`) |
| `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` | — | Alternativa a `DATABASE_URL` |
| `DATABASE_SSL` | `false` | `true` para conectar con SSL (`sslmode=require`) |
| `APP_ENV` | `development` | Nombre del entorno que muestra la UI |
| `GIT_COMMIT` | — | Hash del commit deployado (opcional) |
| `DEPLOYED_AT` | — | Fecha ISO del deploy (opcional) |

Las tablas se crean solas al arrancar (`CREATE TABLE IF NOT EXISTS`). La app reintenta la conexión a la base durante ~30 s antes de fallar.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Dashboard |
| GET | `/health` | Liveness (200 si el proceso vive) |
| GET | `/ready` | Readiness (200 si la base responde, 503 si no) |
| GET | `/api/info` | Info de la app y de la base |
| POST | `/api/visits` | Incrementa y devuelve el contador |
| GET | `/api/messages` | Últimos 50 mensajes |
| POST | `/api/messages` | Crea un mensaje `{ "author", "content" }` |
| GET | `/docs` | Swagger UI generado por FastAPI |

## Correr con Docker (app + Postgres)

```bash
docker compose up -d --build
```

Abrir http://localhost:8000. Si el puerto está ocupado: `APP_PORT=8010 docker compose up -d`.

### Detrás de un antivirus/proxy con inspección TLS (ej. Kaspersky)

Si `pip` falla con `CERTIFICATE_VERIFY_FAILED`, pasar el certificado raíz como build secret (no queda en la imagen). En esta máquina está en `.certs/kaspersky-ca.pem` (ignorado por git):

```bash
docker build --secret id=pip_ca,src=.certs/kaspersky-ca.pem -t sofre-digital-python-test .
docker compose up -d
```

## Correr solo la imagen (Postgres externo)

```bash
docker build -t sofre-digital-python-test .
docker run -d -p 8000:8000 \
  -e DATABASE_URL=postgres://user:pass@host:5432/db \
  -e GIT_COMMIT=$(git rev-parse HEAD) \
  -e DEPLOYED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  sofre-digital-python-test
```

## Correr local sin Docker

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # ajustar valores
uvicorn app.main:app --reload --env-file .env
```
