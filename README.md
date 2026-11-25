# Running REST Services

[![Tests](https://github.com/nicholaselich/runlog/actions/workflows/tests.yml/badge.svg)](https://github.com/nicholaselich/runlog/actions/workflows/tests.yml)


A FastAPI service built with SQLAlchemy and PostgreSQL for storing and analyzing my Strava running data. I love to run and 
wanted to combine one of my passions with learning how to design, create, and test REST services on real data. 

## Architecture

```
Dashboard / CURL 
      |
      v
FastAPI (routers + Pydantic schemas)
      | SQLAlchemy models
      v
Postgres (Docker)
```

- **Router** (`app/routers/`): endpoints
- **Schemas** (`app/schemas.py`): the JSON the API accepts and returns to the client
- **Models** (`app/models.py`): database table as Python classes
- **sql** (`sql/`): the table schema

## Prerequisites
- Python 3.12
- Docker

## Setup

### 1. Start Postgres

```bash
docker run --name runlog-db \
  -e POSTGRES_PASSWORD={PASSWORD} \
  -e POSTGRES_DB=runlog \
  -p 5432:5432 \
  -v runlog-pgdata:/var/lib/postgresql/data \
  -d postgres:16
```

### 2. Create the databases
- `runlog`: production database (already created in Step 1)
- `runlog_test`: test database

```bash
docker exec -i runlog-db psql -U postgres -c "CREATE DATABASE runlog_test;"
```

### 3. Apply the schema
Both databases use the same schema defined in `sql/001_create_activities.sql`. Run the following in order against each database:

```
docker exec -i runlog-db psql -U postgres -d runlog < sql/001_create_activities.sql
docker exec -i runlog-db psql -U postgres -d runlog < sql/002_strava_id_nullable.sql

docker exec -i runlog-db psql -U postgres -d runlog_test < sql/001_create_activities.sql
docker exec -i runlog-db psql -U postgres -d runlog_test < sql/002_strava_id_nullable.sql
```

### 4. Dependencies and Environment Variables
Create a .venv and install dependencies defined in `requirements.txt`

Set environment variables. Create a `.env` file in the project root. `db.py` and `conftest.py` loads the file with python-dotenv.

    DATABASE_URL=postgresql://postgres:{PASSWORD}@localhost:5432/runlog
    TEST_DATABASE_URL=postgresql://postgres:{PASSWORD}@localhost:5432/runlog_test

## Run the Application

Start the FastAPI app locally using Uvicorn:

```bash
uvicorn app.main:app --reload
```

- Swagger UI: <http://127.0.0.1:8000/docs>
- OpenAPI schema: <http://127.0.0.1:8000/openapi.json>
- Health check: <http://127.0.0.1:8000/health>

## API Overview

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/activities` | List activities with optional date, distance, and pagination filters |
| GET | `/v1/activities/{activity_id}` | Get one activity |
| POST | `/v1/activities` | Create an activity |
| PATCH | `/v1/activities/{activity_id}` | Update an activity |
| DELETE | `/v1/activities/{activity_id}` | Delete an activity |
| GET | `/v1/stats/weekly` | Weekly activity totals |
| GET | `/v1/stats/monthly` | Monthly activity totals |

## Running Tests

    pytest -v

Run the test suite for the endpoints. Tests automatically use `runlog_test` through `tests/conftest.py`.

## Dashboard

A small, static web page that charts my running data by calling this API. The dashboard visualizes the results, but more importantly,
gives the API a real consumer that has no database access. The REST layer must do real work: the page can only use what the endpoints
expose.

With the application running, visit:
```
http://127.0.0.1:8000/dashboard/
```

![Runs dashboard](images/runs_dashboard.png)

## Design Decisions
See [DECISIONS.md](DECISIONS.md)

## Known Limitations
1. No authentication
2. List always sorted newest activities first
3. 409 Handler treats any IntegrityError as "already exists"
