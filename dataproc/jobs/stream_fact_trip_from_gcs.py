import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T


def parse_args():
    parser = argparse.ArgumentParser(
        description="Stream fake bike trip JSONL files from GCS and write fact_trip to BigQuery."
    )

    parser.add_argument("--project-id", required=True)
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--checkpoint-path", required=True)
    parser.add_argument("--silver-dataset", default="bike_silver")
    parser.add_argument("--temp-bucket", required=True)
    parser.add_argument("--processing-time", default="30 seconds")
    parser.add_argument("--trigger-once", action="store_true")

    return parser.parse_args()


def main():
    args = parse_args()

    spark = (
        SparkSession.builder
        .appName("stream-fact-trip-from-gcs")
        .getOrCreate()
    )

    spark.conf.set("spark.sql.session.timeZone", "UTC")

    trip_schema = T.StructType([
        T.StructField("trip_id", T.StringType(), True),
        T.StructField("bike_id", T.StringType(), True),
        T.StructField("user_id", T.StringType(), True),
        T.StructField("user_type", T.StringType(), True),
        T.StructField("bike_type", T.StringType(), True),
        T.StructField("start_station_id", T.StringType(), True),
        T.StructField("end_station_id", T.StringType(), True),
        T.StructField("start_time", T.StringType(), True),
        T.StructField("end_time", T.StringType(), True),
        T.StructField("event_created_at", T.StringType(), True),
    ])

    print(f"Reading trip stream from: {args.input_path}")
    print(f"Checkpoint path: {args.checkpoint_path}")

    raw_trip_stream_df = (
        spark.readStream
        .schema(trip_schema)
        .option("maxFilesPerTrigger", 1)
        .json(args.input_path)
    )

    trip_stream_df = (
        raw_trip_stream_df
        .withColumn("trip_id", F.upper(F.trim(F.col("trip_id"))))
        .withColumn("bike_id", F.upper(F.trim(F.col("bike_id"))))
        .withColumn("user_id", F.upper(F.trim(F.col("user_id"))))
        .withColumn("user_type", F.lower(F.trim(F.col("user_type"))))
        .withColumn("bike_type", F.lower(F.trim(F.col("bike_type"))))
        .withColumn("start_station_id", F.upper(F.trim(F.col("start_station_id"))))
        .withColumn("end_station_id", F.upper(F.trim(F.col("end_station_id"))))
        .withColumn("start_time", F.to_timestamp("start_time"))
        .withColumn("end_time", F.to_timestamp("end_time"))
        .withColumn("event_created_at", F.to_timestamp("event_created_at"))
        .withColumn("trip_date", F.to_date("start_time"))
        .withColumn("trip_hour", F.hour("start_time"))
        .withColumn(
            "trip_duration_minutes",
            F.round(
                (F.col("end_time").cast("long") - F.col("start_time").cast("long")) / 60,
                2,
            ),
        )
        .withColumn("is_round_trip", F.col("start_station_id") == F.col("end_station_id"))
        .withColumn("load_dt", F.current_timestamp())
        .withColumn("file_name", F.input_file_name())
    )

    dim_station_table = f"{args.project_id}:{args.silver_dataset}.dim_station"

    print(f"Reading static station dimension from: {dim_station_table}")

    dim_station_df = (
        spark.read
        .format("bigquery")
        .option("table", dim_station_table)
        .load()
        .filter(F.col("is_active") == True)
        .select(
            "station_id",
            "station_name",
            "neighbourhood",
            "capacity",
        )
    )

    start_station_df = (
        dim_station_df
        .select(
            F.col("station_id").alias("start_station_id"),
            F.col("station_name").alias("start_station_name"),
            F.col("neighbourhood").alias("start_neighbourhood"),
            F.col("capacity").alias("start_station_capacity"),
        )
    )

    end_station_df = (
        dim_station_df
        .select(
            F.col("station_id").alias("end_station_id"),
            F.col("station_name").alias("end_station_name"),
            F.col("neighbourhood").alias("end_neighbourhood"),
            F.col("capacity").alias("end_station_capacity"),
        )
    )

    enriched_trip_stream_df = (
        trip_stream_df
        .join(F.broadcast(start_station_df), on="start_station_id", how="left")
        .join(F.broadcast(end_station_df), on="end_station_id", how="left")
        .withColumn("is_valid_start_station", F.col("start_station_name").isNotNull())
        .withColumn("is_valid_end_station", F.col("end_station_name").isNotNull())
        .withColumn(
            "is_valid_trip",
            F.col("trip_id").isNotNull()
            & F.col("bike_id").isNotNull()
            & F.col("start_time").isNotNull()
            & F.col("end_time").isNotNull()
            & (F.col("trip_duration_minutes") > 0)
            & F.col("is_valid_start_station")
            & F.col("is_valid_end_station"),
        )
        .select(
            "trip_id",
            "bike_id",
            "user_id",
            "user_type",
            "bike_type",
            "start_station_id",
            "start_station_name",
            "start_neighbourhood",
            "start_station_capacity",
            "end_station_id",
            "end_station_name",
            "end_neighbourhood",
            "end_station_capacity",
            "start_time",
            "end_time",
            "trip_date",
            "trip_hour",
            "trip_duration_minutes",
            "is_round_trip",
            "is_valid_start_station",
            "is_valid_end_station",
            "is_valid_trip",
            "event_created_at",
            "load_dt",
            "file_name",
        )
    )

    target_table = f"{args.project_id}:{args.silver_dataset}.fact_trip"

    print(f"Writing stream output to: {target_table}")

    def write_batch_to_bigquery(batch_df, batch_id):
        batch_count = batch_df.count()

        print(f"Batch {batch_id} row count before dedupe: {batch_count}")

        if batch_count == 0:
            print(f"Batch {batch_id} is empty. Skipping write.")
            return

        clean_batch_df = batch_df.dropDuplicates(["trip_id"])

        final_count = clean_batch_df.count()
        print(f"Batch {batch_id} row count after dedupe: {final_count}")

        clean_batch_df.show(10, truncate=False)

        (
            clean_batch_df.write
            .format("bigquery")
            .option("table", target_table)
            .option("temporaryGcsBucket", args.temp_bucket)
            .option("writeMethod", "indirect")
            .mode("append")
            .save()
        )

        print(f"Batch {batch_id}: successfully wrote {final_count} records to {target_table}")

    writer = (
        enriched_trip_stream_df.writeStream
        .foreachBatch(write_batch_to_bigquery)
        .option("checkpointLocation", args.checkpoint_path)
        .outputMode("append")
    )

    if args.trigger_once:
        query = writer.trigger(once=True).start()
    else:
        query = writer.trigger(processingTime=args.processing_time).start()

    query.awaitTermination()
    spark.stop()


if __name__ == "__main__":
    main()