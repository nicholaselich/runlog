"""
Load runs from a Strava export (activities.csv) into the Postgres `activities` table.

Usage:
    export DATABASE_URL="postgresql://postgres:dev@localhost:5432/runlog"
    python scripts/load_data.py                 # load for real
    python scripts/load_data.py --dry-run       # parse and validate only, no database
    python scripts/load_data.py path/to/file.csv

Safe to run more than once: rows are upserted on strava_activity_id.
"""
import csv
import os
import sys
from datetime import datetime, timezone

DEFAULT_CSV = "data/strava_export/activities.csv"

# Which Strava activity types count as runs. Add "Trail Run", "Virtual Run", etc. if you want them.
RUN_TYPES = {"Run"}

DATE_FORMAT = "%b %d, %Y, %I:%M:%S %p"  # e.g. "Nov 8, 2026, 8:18:28 PM" (export is UTC)

# Header names in the Strava export (English). Duplicated headers use the LAST column,
# which in the export is the one in meters / seconds.
NEEDED = [
    "Activity ID", "Activity Date", "Activity Type", "Elapsed Time", "Moving Time",
    "Distance", "Max Heart Rate", "Average Heart Rate", "Elevation Gain",
    "Elevation Loss", "Calories", "Total Steps",
]

UPSERT_SQL = """
INSERT INTO activities (
    strava_activity_id, start_time, activity_type, elapsed_time, moving_time,
    distance, max_heartrate, avg_heartrate, elevation_gain, elevation_loss,
    calories, steps
) VALUES (
    %(strava_activity_id)s, %(start_time)s, %(activity_type)s, %(elapsed_time)s, %(moving_time)s,
    %(distance)s, %(max_heartrate)s, %(avg_heartrate)s, %(elevation_gain)s, %(elevation_loss)s,
    %(calories)s, %(steps)s
)
ON CONFLICT (strava_activity_id) DO UPDATE SET
    start_time     = EXCLUDED.start_time,
    activity_type  = EXCLUDED.activity_type,
    elapsed_time   = EXCLUDED.elapsed_time,
    moving_time    = EXCLUDED.moving_time,
    distance       = EXCLUDED.distance,
    max_heartrate  = EXCLUDED.max_heartrate,
    avg_heartrate  = EXCLUDED.avg_heartrate,
    elevation_gain = EXCLUDED.elevation_gain,
    elevation_loss = EXCLUDED.elevation_loss,
    calories       = EXCLUDED.calories,
    steps          = EXCLUDED.steps
"""


def to_float(text):
    """Blank -> None, otherwise a float. Missing stays NULL, never 0."""
    text = (text or "").strip().replace(",", "")
    return float(text) if text else None


def to_int(text):
    value = to_float(text)
    return None if value is None else int(round(value))


def clean_row(row, col):
    """Turn one raw CSV row (list of strings) into a dict ready for the database.
    Raises ValueError with a readable reason if the row can't be used."""
    get = lambda name: row[col[name]]

    start = datetime.strptime(get("Activity Date").strip(), DATE_FORMAT).replace(tzinfo=timezone.utc)
    cleaned = {
        "strava_activity_id": int(get("Activity ID")),
        "start_time": start,
        "activity_type": get("Activity Type").strip(),
        "elapsed_time": to_int(get("Elapsed Time")),
        "moving_time": to_int(get("Moving Time")),
        "distance": to_float(get("Distance")),
        "max_heartrate": to_int(get("Max Heart Rate")),
        "avg_heartrate": to_int(get("Average Heart Rate")),
        "elevation_gain": to_float(get("Elevation Gain")),
        "elevation_loss": to_float(get("Elevation Loss")),
        "calories": to_int(get("Calories")),
        "steps": to_int(get("Total Steps")),
    }

    # Mirror the table's rules so one bad row is skipped instead of crashing the load.
    for field in ("elapsed_time", "moving_time", "distance"):
        if cleaned[field] is None or cleaned[field] <= 0:
            raise ValueError(f"{field} missing or not positive ({cleaned[field]})")
    if cleaned["moving_time"] > cleaned["elapsed_time"]:
        raise ValueError("moving_time is greater than elapsed_time")
    return cleaned


def read_runs(path):
    """Read the CSV and return (rows_to_load, total_rows, skipped_non_runs, skipped_bad)."""
    runs, total, non_runs, bad = [], 0, 0, 0

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)

        # Map each header name to the LAST column with that name (handles duplicate headers).
        col = {}
        for i, name in enumerate(header):
            col[name.strip()] = i
        missing = [n for n in NEEDED if n not in col]
        if missing:
            sys.exit(f"Missing expected columns: {missing}\nHeader in file: {header}")

        print("Columns used (name -> position):")
        for name in NEEDED:
            dupes = sum(1 for h in header if h.strip() == name)
            note = f"  (header appears {dupes}x, using the last)" if dupes > 1 else ""
            print(f"  {name} -> {col[name]}{note}")

        for line_no, row in enumerate(reader, start=2):  # line 1 is the header
            if not row:
                continue
            total += 1
            if row[col["Activity Type"]].strip() not in RUN_TYPES:
                non_runs += 1
                continue
            try:
                runs.append(clean_row(row, col))
            except (ValueError, IndexError) as e:
                bad += 1
                print(f"  skipped line {line_no}: {e}")

    return runs, total, non_runs, bad


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    path = args[0] if args else DEFAULT_CSV

    runs, total, non_runs, bad = read_runs(path)
    print(f"\nRead {total} rows: {len(runs)} runs ok, {non_runs} not runs, {bad} skipped as bad.")

    if runs:
        print("\nFirst cleaned row (check this against Strava):")
        for key, value in runs[0].items():
            print(f"  {key}: {value}")

    if dry_run:
        print("\nDry run: nothing was written to the database.")
        return

    import psycopg  # imported here so --dry-run works without a database

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_SQL, runs)
        # leaving the `with conn` block commits the transaction
        count = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    print(f"\nUpserted {len(runs)} runs. Table now has {count} rows.")


if __name__ == "__main__":
    main()
