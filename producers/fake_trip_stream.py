import argparse
import csv
import json
import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.cloud import storage


USER_TYPES = ["member", "casual"]
BIKE_TYPES = ["classic", "e-bike"]


def load_station_ids(station_file: str) -> list[str]:
    station_ids = []

    with open(station_file, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row.get("is_active", "").lower() == "true":
                station_ids.append(row["station_id"])

    if not station_ids:
        raise ValueError("No active stations found in station file.")

    return station_ids


def generate_trip_event(station_ids: list[str]) -> dict:
    start_station = random.choice(station_ids)
    end_station = random.choice(station_ids)

    start_time = datetime.now(timezone.utc)
    duration_minutes = random.randint(3, 45)
    end_time = start_time + timedelta(minutes=duration_minutes)

    return {
        "trip_id": f"TRIP_{uuid.uuid4().hex[:12].upper()}",
        "bike_id": f"BK{random.randint(1, 500):04d}",
        "user_id": f"USER_{random.randint(1, 10000):05d}",
        "user_type": random.choice(USER_TYPES),
        "bike_type": random.choice(BIKE_TYPES),
        "start_station_id": start_station,
        "end_station_id": end_station,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "event_created_at": datetime.now(timezone.utc).isoformat(),
    }


def upload_jsonl_to_gcs(
    bucket_name: str,
    prefix: str,
    records: list[dict],
) -> str:
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    now = datetime.now(timezone.utc)
    date_path = now.strftime("ingest_date=%Y-%m-%d")
    file_name = f"trip_events_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jsonl"

    object_name = f"{prefix.rstrip('/')}/{date_path}/{file_name}"

    payload = "\n".join(json.dumps(record) for record in records)

    blob = bucket.blob(object_name)
    blob.upload_from_string(payload, content_type="application/json")

    return f"gs://{bucket_name}/{object_name}"


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--station-file",
        required=True,
        help="Local path to station CSV file.",
    )

    parser.add_argument(
        "--bucket",
        required=True,
        help="Cloud Storage bucket name.",
    )

    parser.add_argument(
        "--prefix",
        default="raw/trips",
        help="Cloud Storage prefix for trip event files.",
    )

    parser.add_argument(
        "--events-per-batch",
        type=int,
        default=25,
        help="Number of trip events to write per JSONL file.",
    )

    parser.add_argument(
        "--sleep-seconds",
        type=int,
        default=10,
        help="Seconds to wait between batches.",
    )

    parser.add_argument(
        "--max-batches",
        type=int,
        default=0,
        help="Number of batches to generate. Use 0 to run forever.",
    )

    args = parser.parse_args()

    station_file = Path(args.station_file)

    if not station_file.exists():
        raise FileNotFoundError(f"Station file not found: {station_file}")

    station_ids = load_station_ids(str(station_file))

    batch_count = 0

    print(f"Loaded {len(station_ids)} active stations.")
    print(f"Writing fake trip events to gs://{args.bucket}/{args.prefix}")

    while True:
        batch_count += 1

        records = [
            generate_trip_event(station_ids)
            for _ in range(args.events_per_batch)
        ]

        gcs_path = upload_jsonl_to_gcs(
            bucket_name=args.bucket,
            prefix=args.prefix,
            records=records,
        )

        print(f"Batch {batch_count}: wrote {len(records)} events to {gcs_path}")

        if args.max_batches > 0 and batch_count >= args.max_batches:
            break

        time.sleep(args.sleep_seconds)


if __name__ == "__main__":
    main()