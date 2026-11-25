# Running REST Services

## Database Setup

The application uses PostgreSQL running in Docker

### Database

- `runlog`: production database
- `runlog_test`: test database

Both databases use the same schema defined in `sql/001_create_activities.sql`. Run the following in order against each database:

```
docker exec -i runlog-db psql -U postgres -d runlog < sql/001_create_activities.sql
docker exec -i runlog-db psql -U postgres -d runlog < sql/002_strava_id_nullable.sql

docker exec -i runlog-db psql -U postgres -d runlog_test < sql/001_create_activities.sql
docker exec -i runlog-db psql -U postgres -d runlog_test < sql/002_strava_id_nullable.sql
```

### Environment Variables

Create a `.env` file in the project root:

    DATABASE_URL=postgresql://postgres:{PASSWORD}@localhost:5432/runlog
    TEST_DATABASE_URL=postgresql://postgres:{PASSWORD}@localhost:5432/runlog_test

### Initialize Test Database

Create the test database:

    docker exec -it runlog-db psql -U postgres -c "CREATE DATABASE runlog_test;"

Apply the schema:

    docker exec -i runlog-db psql -U postgres -d runlog_test < sql/001_create_activities.sql

### Running Tests

    pytest -v

Tests automatically use `runlog_test` through `tests/conftest.py`.

## Running the Application

Start the FASTAPI app locally using Uvicorn and open in a browser http://127.0.0.1:8000

``` 
uvicorn app.main:app --reload
```

The --reload flag automatically restarts the server when code changes are detected. 

## API Documentation
Interactive API documentation available through FASTAPI's built-in Swagger UI

With the application running

- Swagger UI: http://localhost:8000/docs
- OpenAPI Schema: http://localhost:8000/openapi.json

## Dashboard

A small, static web page that charts my running data by calling this API. The dashboard visualizes the results, but more importantly,
gives the API a real consumer that has no database access. The REST layer must do real work: the page can only use what the endpoints
expose.

With the application running, visit:
```
http://127.0.0.1:8000/dashboard/
```

![Runs dashboard](images/runs_dashboard.png)


## Potential Future Improvements
1. Sorting is fixed (newest activities first); a sort parameter is a possible later addition

## Limitations
1. No authentication
2. 409 Handler treats any IntegrityError as "already exists"
