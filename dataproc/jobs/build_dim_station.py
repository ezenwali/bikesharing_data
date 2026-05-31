import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T


def parse_args():
    parser = argparse.ArgumentParser(description="Build bike_silver.dim_station from station CSV in GCS.")

    parser.add_argument(
        "--project-id",
        required=True,
        help="GCP project ID.",
    )

    parser.add_argument(
        "--station-path",
        required=True,
        help="GCS path to station CSV file.",
    )

    parser.add_argument(
        "--silver-dataset",
        default="bike_silver",
        help="BigQuery silver dataset name.",
    )

    parser.add_argument(
        "--temp-bucket",
        required=True,
        help="Temporary GCS bucket for the Spark BigQuery connector.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    spark = (
        SparkSession.builder
        .appName("build-dim-station")
        .getOrCreate()
    )

    station_schema = T.StructType([
        T.StructField("station_id", T.StringType(), True),
        T.StructField("station_name", T.StringType(), True),
        T.StructField("latitude", T.DoubleType(), True),
        T.StructField("longitude", T.DoubleType(), True),
        T.StructField("capacity", T.IntegerType(), True),
        T.StructField("neighbourhood", T.StringType(), True),
        T.StructField("is_active", T.BooleanType(), True),
        T.StructField("launch_date", T.DateType(), True),
    ])

    print(f"Reading station file from: {args.station_path}")

    raw_station_df = (
        spark.read
        .option("header", True)
        .option("mode", "FAILFAST")
        .schema(station_schema)
        .csv(args.station_path)
    )

    raw_count = raw_station_df.count()
    print(f"Raw station row count: {raw_count}")

    if raw_count == 0:
        raise ValueError("Station file is empty. No records found.")

    dim_station_df = (
        raw_station_df
        .withColumn("station_id", F.upper(F.trim(F.col("station_id"))))
        .withColumn("station_name", F.trim(F.col("station_name")))
        .withColumn("neighbourhood", F.trim(F.col("neighbourhood")))
        .withColumn("station_key", F.sha2(F.col("station_id"), 256))
        .withColumn("load_dt", F.current_timestamp())
        .withColumn("file_name", F.input_file_name())
        .filter(F.col("station_id").isNotNull())
        .filter(F.col("station_id") != "")
        .dropDuplicates(["station_id"])
        .select(
            "station_key",
            "station_id",
            "station_name",
            "latitude",
            "longitude",
            "capacity",
            "neighbourhood",
            "is_active",
            "launch_date",
            "load_dt",
            "file_name",
        )
    )

    final_count = dim_station_df.count()
    print(f"Final dim_station row count: {final_count}")

    if final_count == 0:
        raise ValueError("dim_station output is empty after cleaning.")

    print("Preview of dim_station:")
    dim_station_df.show(10, truncate=False)

    # Use project:dataset.table format for Spark BigQuery connector.
    target_table = f"{args.project_id}:{args.silver_dataset}.dim_station"

    print(f"Writing dim_station to BigQuery table: {target_table}")
    print(f"Using temporary GCS bucket: {args.temp_bucket}")

    (
        dim_station_df.write
        .format("bigquery")
        .option("table", target_table)
        .option("temporaryGcsBucket", args.temp_bucket)
        .option("writeMethod", "indirect")
        .mode("overwrite")
        .save()
    )

    print(f"Successfully wrote dim_station to {target_table}")

    spark.stop()


if __name__ == "__main__":
    main()