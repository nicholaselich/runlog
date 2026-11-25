# Running-RESTful-Services

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


### Potential Future Improvements
1. Sorting is fixed (newest activities first); a sort parameter is a possible later addition

### Limitations
1. Tests run against the database
2. No authentication
3. 409 Handler treats any IntegrityError as "already exists"
