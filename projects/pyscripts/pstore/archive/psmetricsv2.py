import time
import logging
from google.cloud import monitoring_v3
from google.cloud.monitoring_v3.services.metric_service import pagers

CONFIG = {
    "parallelstore": {
        "project_id": "thomashk-mig",
        # IMPORTANT: Verify this is the ACTUAL Parallelstore instance name, not a PVC name.
        "instance_id": "pvc-d13842ae-2bd4-4602-bd11-002eb1197011", # Update if necessary!
        "region": "us-central1" # Use region, not zone, if needed elsewhere.
    }
}

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Set to logging.DEBUG for more verbose output from fetch_metric

file_handler = logging.FileHandler('parallelstore_metrics.log', mode='a')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Optional: StreamHandler for console output
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
# --- End Logging Setup ---

def fetch_metric(metric_type: str, project_id_str: str, instance_id_str: str) -> float | None:
    """
    Query Cloud Monitoring API for Parallelstore metrics using ALIGN_RATE
    and return the max rate value over the queried period.
    """
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id_str}"

    # Query last 30 minutes of data
    end_time_seconds = time.time()
    start_time_seconds = end_time_seconds - 1800 # 30 minutes * 60 seconds/minute
    interval = monitoring_v3.types.TimeInterval(
        end_time={"seconds": int(end_time_seconds)},
        start_time={"seconds": int(start_time_seconds)}
    )

    # Define aggregation to align to 60-second periods and calculate the rate.
    # This will give values in units/second (e.g., ops/sec, bytes/sec).
    aggregation = monitoring_v3.types.Aggregation(
        alignment_period={"seconds": 60},
        per_series_aligner=monitoring_v3.types.Aggregation.Aligner.ALIGN_RATE,
        # REDUCE_MAX takes the max rate across any time series if multiple match the filter (unlikely for a single instance_id)
        # If you are certain only one series will ever match, REDUCE_NONE is also fine.
        cross_series_reducer=monitoring_v3.types.Aggregation.Reducer.REDUCE_MAX
    )

    filter_str = f'metric.type="{metric_type}" AND resource.type = "parallelstore.googleapis.com/Instance" AND resource.label.instance_id="{instance_id_str}"'

    request = monitoring_v3.types.ListTimeSeriesRequest(
        name=project_name,
        filter=filter_str,
        interval=interval,
        view=monitoring_v3.types.ListTimeSeriesRequest.TimeSeriesView.FULL,
        aggregation=aggregation # Apply the aggregation for rate calculation
    )

    logger.debug(f"Fetching metric: {metric_type} for instance: {instance_id_str} in project: {project_id_str}")
    logger.debug(f"Filter: {filter_str}")
    logger.debug(f"Aggregation: Align_Rate over 60s")

    try:
        results: pagers.ListTimeSeriesPager = client.list_time_series(request=request)
        values = []
        for page in results.pages: # Iterate through pages if there are many time series (unlikely here)
            for ts in page.time_series:
                for point in ts.points:
                    # ALIGN_RATE typically results in double_value
                    if point.value.double_value is not None:
                        values.append(point.value.double_value)
                    # Handle cases where int64 might still appear, though less likely with ALIGN_RATE
                    elif point.value.int64_value is not None:
                         values.append(float(point.value.int64_value))


        logger.debug(f"Rate values for {metric_type}: {values}")
        return max(values) if values else None
    except Exception as e:
        logger.error(f"Error fetching metric {metric_type} for {instance_id_str}: {e}", exc_info=True)
        # Depending on the error, you might get more details here.
        # Common errors include PermissionDenied, NotFound (if instance_id or metric is wrong).
        raise # Re-raise the exception if you want the main script to catch it, or handle here.


def validate_parallelstore_metrics():
    """
    Fetches and validates Parallelstore IOPS and throughput using Cloud Monitoring API.
    Assumes metrics fetched are rates (per second).
    """
    project_id = CONFIG["parallelstore"]["project_id"]
    instance_id = CONFIG["parallelstore"]["instance_id"]

    # Expected benchmarks (update based on GCP docs for your instance type/capacity)
    # These should be in units/second if using ALIGN_RATE for fetching.
    EXPECTED_IOPS_PER_SECOND = 30000
    EXPECTED_THROUGHPUT_MBPS = 1150 # MB/s (MegaBYTES per second, not Mebibytes)

    # Metric names
    # For IOPS, you might want to sum read_ops_count and write_ops_count, or check them separately.
    # Here, we are just checking read_ops_count.
    read_iops_metric = "parallelstore.googleapis.com/instance/read_ops_count"
    # write_iops_metric = "parallelstore.googleapis.com/instance/write_ops_count" # Optional
    throughput_metric = "parallelstore.googleapis.com/instance/transferred_byte_count" # This includes read and write bytes

    logger.info(f"Fetching metrics for instance: {instance_id} in project: {project_id}")

    # Fetch metrics as rates (ops/sec, bytes/sec)
    actual_read_iops_per_second = fetch_metric(read_iops_metric, project_id, instance_id)
    actual_throughput_bytes_per_second = fetch_metric(throughput_metric, project_id, instance_id)

    actual_throughput_mbps = None
    if actual_throughput_bytes_per_second is not None:
        actual_throughput_mbps = actual_throughput_bytes_per_second / (1000**2) # MB/s (10^6 bytes)
        # If you prefer MiB/s (2^20 bytes):
        # actual_throughput_mibps = actual_throughput_bytes_per_second / (1024**2)
        # Make sure your EXPECTED_THROUGHPUT_MBPS uses the same unit definition.

    logger.info(f"Retrieved Parallelstore Metrics for instance {instance_id}:")
    logger.info(f"Max Read IOPS (rate): {actual_read_iops_per_second} ops/sec (Expected: >= {EXPECTED_IOPS_PER_SECOND} ops/sec)")
    logger.info(f"Max Throughput (rate): {actual_throughput_mbps} MBps (Expected: >= {EXPECTED_THROUGHPUT_MBPS} MBps)")

    validation_passed = True
    if actual_read_iops_per_second is None or actual_read_iops_per_second < EXPECTED_IOPS_PER_SECOND:
        logger.error(f"Read IOPS rate too low: {actual_read_iops_per_second} ops/sec. Expected >= {EXPECTED_IOPS_PER_SECOND} ops/sec")
        validation_passed = False
    else:
        logger.info(f"Read IOPS rate check passed: {actual_read_iops_per_second} ops/sec >= {EXPECTED_IOPS_PER_SECOND} ops/sec")

    if actual_throughput_mbps is None or actual_throughput_mbps < EXPECTED_THROUGHPUT_MBPS:
        logger.error(f"Throughput rate too low: {actual_throughput_mbps} MBps. Expected >= {EXPECTED_THROUGHPUT_MBPS} MBps")
        validation_passed = False
    else:
        logger.info(f"Throughput rate check passed: {actual_throughput_mbps} MBps >= {EXPECTED_THROUGHPUT_MBPS} MBps")

    if validation_passed:
        logger.info("Parallelstore performance (based on fetched rates) meets or exceeds expected GCP benchmarks!")
    else:
        logger.warning("Parallelstore performance (based on fetched rates) DOES NOT meet expected GCP benchmarks.")

    return validation_passed


if __name__ == "__main__":
    logger.info("Starting Parallelstore metrics validation...")
    try:
        # Before running, ensure:
        # 1. `gcloud auth application-default login` has been run with correct user OR
        #    `GOOGLE_APPLICATION_CREDENTIALS` env var is set to a valid service account key file.
        # 2. The project in `CONFIG` has "Cloud Monitoring API" enabled.
        # 3. The `instance_id` in `CONFIG` is the correct Parallelstore instance name.
        # 4. The user/SA has at least 'roles/monitoring.viewer' on the project.
        success = validate_parallelstore_metrics()
        if success:
            logger.info("Validation completed successfully (metrics met expectations).")
        else:
            logger.error("Validation completed with failures (metrics did not meet expectations or data was missing).")
    except Exception as e:
        # This will catch errors from fetch_metric if they are re-raised, or other unexpected errors.
        logger.error(f"An critical error occurred during Parallelstore metrics validation: {e}", exc_info=True)
        logger.error("Please check authentication, permissions, API enablement, and instance identifiers.")