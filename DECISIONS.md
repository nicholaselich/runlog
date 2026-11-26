# Design Decisions

## Data and Schema

### Activity Type
- **Chose:** I chose to focus on runs exclusively, but kept `activity_type` because there are different types of runs (Run, Trail Run, etc.)
- **Alternatives:** I could have kept all Strava activities such as Hikes and Walks and allowed the user to specify the activity type
- **Why:** I wanted this to be a project focused on running because running is my favorite sport tracked by Strava.
- **Tradeoffs:** No significant cost. If perhaps I had more non-running activities, perhaps I would have expanded the activity type scope

## Duplicate Column Names
- **Situation:** Exported Strava data file provided duplicate columns for variables like `Distance` and `Elapsed Time`. 
- **Chose:** Columns were different based on the units/precision of the value. `Distance` columns, for example, had values of 5.12 (km) and 5119.1 (m). After cross-referencing with the activity in my Strava profile to verify, I chose the columns with more precision and dropped the corresponding duplicates.
- **Why:** I would rather have the more precise data option, if given the choice.
- **Possible Brittleness:** The data importer script pulls the last occurrence of each column. If the column order in the export were to change or the units were to change, future data loads would require a script modification. 

### Own primary key and unique Strava ID
- **Chose:** `id` is the Postgres-generated identity column and the PK. `strava_activity_id` is its own column with a UNIQUE constraint
- **Alternatives:** Use `strava_activity_id` as the primary key
- **Why:** 
    - Not every run comes from Strava. A manually entered run could have a null `strava_activity_id` and a PK cannot have a NULL value
    - API URLs use the Postgres-generated ID so the API doesn't depend on Strava identifiers
- **Tradeoffs:** Two IDs and an extra index. If the project only had Strava data, then Strava ID could serve as the key and the Postgres-generated ID column could be dropped

### Nullable and Immutable Strava ID
- **Chose:** `strava_activity_id` can be NULL
- **Alternatives:** `strava_activity_id` cannot be NULL; require one on every run and generate a fake ID for manual runs. Also allow it to be editable
- **Why:** 
    - A run that is entered manually doesn't have a Strava ID and generating a fake one would pollute the data
    - I initially made the column `NOT NULL`, but when I wrote the CREATE schema, I thought it would be better to allow `None`, so a manual run wouldn't fail. I changed the table with `sql/002_strava_id_nullable.sql`
    - It's the identity of the Strava record, so once it's created by Strava, it really should not be changed.
- **Tradeoff:** PATCH doesn't support updating `strava_activity_id` so ID mistakes can't be fixed without deleting the entry and recreating the run

### Timestamps
- **Chose:** Timestamps are stored in UTC and require a timezone, so naive datetimes don't introduce ambiguity
- **Alternatives:** Timestamps could have been stored in their local time zones
- **Why:** Local time is disregarded, but given the possibility of runs in different time zones, standardizing to UTC made sense to ensure consistency
- **Tradeoffs:** Further development that might introduce metrics or visualizations that use the local time zone would be difficult

### Missing Heart Rate, Calories, and Steps
- **Chose:** If missing, values are stored as NULL
- **Alternatives:** Values could have been stored as 0
- **Why:** NULL distinguishes "not recorded" from a real zero
- **Tradeoffs:** Consumers must handle missing values

### CHECK Constraints
- **Chose:** Add four CHECK constraints to enforce positive elapsed time, moving time, and distance, and ensure moving time doesn't exceed elapsed time
- **Alternatives:** Rely only on API validation, or allow invalid values into the database
- **Why:** Database constraints protect data integrity for all the write paths. API validation provides clean errors to clients
- **Tradeoffs:** The same rules are defined in both the API schema and database, so they must stay in sync

## API Design and Testing

### API Version Prefix
- **Chose:** Prefix API routes with v1
- **Alternatives:** Use unversioned routes
- **Why:** Identifies the API version and leaves room for future versions
- **Tradeoffs:** The version must be maintained in the route definitions and in client code

### Separate Database Models and API Schemas
- **Chose:** Define SQLAlchemy models for database tables and Pydantic schemas for GET/POST/DELETE/PATCH
- **Alternatives:** Use one model for both the database and the API requests/responses
- **Why:** The database and API have different responsibilities 
    - SQLAlchemy is responsible for defining a column such as `distance` in the database as `distance`
    - Pydantic is responsible for exposing `distance` as `distance_m` and defining which fields clients can see or submit
- **Tradeoffs:** There is some overlap in the fields

### Dependency Injection with `Depends(get_db)`
- **Chose:** Provide database sessions with FastAPI's `Depends(get_db)` 
- **Alternatives:** Create sessions in each endpoint in `routers/`
- **Why:** `get_db` gives each request its own session and handles creation and cleanup in one place. It also keeps the database connection separate from the endpoint logic
- **Tradeoffs:** It takes an extra step to see where the endpoint gets its database session (`get_db`)

### Pagination
- **Chose:** Limit + Offset pagination
- **Alternatives:** Use cursor pagination
- **Why:** Limit + offset works well for a project of this scale
- **Tradeoffs:** Large offsets could be slow if there was a massive increase in the amount of data in the DB
- **When to switch:** If there was a sufficiently large amount of data that impacted limit + offset performance or if new activities were being added while clients were accessing the data, it would be best to switch to cursor-based pagination

### From and To 
- **Chose:** For the list activities and stats endpoints, treat `From` and `To` as inclusive
- **Alternatives:** `From` and `To` could have been exclusive or any combination of inclusive/exclusive
- **Why:** People expect a selected date range to include both dates. Using the same rule across endpoints keeps their results consistent
- **Tradeoffs:** The end date is implemented as before midnight on the following day - instead of `<= to_date` - to include the full day

### JSON Field Names with Units
- **Chose:** Include units in JSON field names such as `distance_m`
- **Alternatives:** Present JSON field names without units such as `distance`
- **Why:** Providing units removes any ambiguity about the returned measurements
- **Tradeoffs:** Field names are longer and column names must be mapped in the Pydantic schema

### PATCH `exclude_unset`
- **Chose:** Use `model_dump(exclude_unset=True)` so PATCH updates only fields that the client provides
- **Why:** We don't want omitted fields to be changed in any way. If a field needs to be cleared out, then a client can explicitly provide NULL for that column. Without this parameter, omitted optional fields could be incorrectly updated to NULL
- **Time Validation:** Check `moving_time <= elapsed_time` in the PATCH to validate the updated record still adheres to the constraint

### Separate Test Database
- **Chose:** Run tests against a test database and generate records the tests need
- **Alternatives:** Use the production database and clean up after each test
- **Why:** Tests need predictable and isolated data. Leftover rows from my previous `pytest` runs were causing issues with future test runs. For example, tests that expected a specific activity count would see records created from old tests causing a failure
- **Tradeoffs:** An additional test database must be created, and each test must create + clean up synthetic test records
