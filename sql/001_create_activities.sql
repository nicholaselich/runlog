CREATE TABLE activities (
id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
strava_activity_id BIGINT NOT NULL UNIQUE,
start_time TIMESTAMPTZ NOT NULL,
activity_type TEXT NOT NULL,
elapsed_time INTEGER NOT NULL,
moving_time INTEGER NOT NULL,
distance DOUBLE PRECISION NOT NULL,
max_heartrate SMALLINT,
avg_heartrate SMALLINT,
elevation_gain DOUBLE PRECISION,
elevation_loss DOUBLE PRECISION,
calories INTEGER,
steps INTEGER,

CONSTRAINT elapsed_time_positive CHECK (elapsed_time > 0),
CONSTRAINT moving_time_positive CHECK (moving_time > 0),
CONSTRAINT distance_positive CHECK (distance > 0),
CONSTRAINT moving_le_elapsed CHECK (moving_time <= elapsed_time)

);
