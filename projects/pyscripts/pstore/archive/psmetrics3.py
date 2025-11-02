import time
import logging
from google.cloud import monitoring_v3
from google.cloud.monitoring_v3.services.metric_service import pagers
from datetime import datetime, timezone, timedelta # Added timedelta for date iteration

# --- Configuration ---
# TODO: IMPORTANT - Verify these values for your environment
CONFIG = {
    "parallelstore": {
        "project_id": "thomashk-mig",  # Your GCP Project ID
        # IMPORTANT: This MUST be the actual Parallelstore instance name/ID
        # as seen in the GCP Filestore console, NOT a PVC name unless they are identical.
        "instance_id": "tpu-home-test", # VERIFY THIS!
        "region": "us-central1" # The REGION of your Parallelstore instance
    }
}

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Set to logging.DEBUG for more verbose API call details

# File Handler for logging to a file
file_handler = logging.FileHandler('parallelstore_metrics_over_time.log', mode='a') # Changed log file name
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Stream Handler for logging to the console
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter) # Using the same formatter
logger.addHandler(stream_handler)
# --- End Logging Setup ---

def fetch_metric(
    metric_type: str,
    project_id_str: str,
    instance_id_str: str,
    query_start_time: datetime,
    query_end_time: datetime
) -> float | None:
    """
    Query Cloud Monitoring API for Parallelstore metrics using ALIGN_RATE
    and return the max rate value over the specified query period.
    """
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id_str}"

    start_time_seconds = int(query_start_time.timestamp())
    end_time_seconds = int(query_end_time.timestamp())

    interval = monitoring_v3.types.TimeInterval(
        end_time={"seconds": end_time_seconds},
        start_time={"seconds": start_time_seconds}
    )

    aggregation = monitoring_v3.types.Aggregation(
        alignment_period={"seconds": 60},
        per_series_aligner=monitoring_v3.types.Aggregation.Aligner.ALIGN_RATE,
        cross_series_reducer=monitoring_v3.types.Aggregation.Reducer.REDUCE_MAX
    )

    filter_str = f'metric.type="{metric_type}" AND resource.type = "parallelstore.googleapis.com/Instance" AND resource.label.instance_id="{instance_id_str}"'

    request = monitoring_v3.types.ListTimeSeriesRequest(
        name=project_name,
        filter=filter_str,
        interval=interval,
        view=monitoring_v3.types.ListTimeSeriesRequest.TimeSeriesView.FULL,
        aggregation=aggregation
    )

    logger.debug(f"Fetching metric: {metric_type} for instance: {instance_id_str} in project: {project_id_str}")
    logger.debug(f"Query Window: {query_start_time.isoformat()} to {query_end_time.isoformat()}")
    logger.debug(f"Filter: {filter_str}")
    logger.debug(f"Aggregation: Aligner=ALIGN_RATE, Alignment Period=60s, Reducer=REDUCE_MAX")

    try:
        results: pagers.ListTimeSeriesPager = client.list_time_series(request=request)
        values = []
        for page in results.pages:
            for ts in page.time_series:
                for point in ts.points:
                    if point.value.double_value is not None:
                        values.append(point.value.double_value)
                    elif point.value.int64_value is not None:
                         values.append(float(point.value.int64_value))

        logger.debug(f"Rate values for {metric_type} (from {query_start_time.strftime('%Y-%m-%d')} to {query_end_time.strftime('%Y-%m-%d')}): {values}")
        return max(values) if values else None
    except Exception as e:
        logger.error(f"Error fetching metric {metric_type} for {instance_id_str} over window {query_start_time.isoformat()} to {query_end_time.isoformat()}: {e}", exc_info=True)
        raise

def log_daily_performance_over_period(start_date_overall: datetime, end_date_overall: datetime):
    """
    Fetches and logs daily peak performance metrics for Parallelstore
    over a specified period.
    """
    project_id = CONFIG["parallelstore"]["project_id"]
    instance_id = CONFIG["parallelstore"]["instance_id"]

    # TODO: Update these expected benchmarks if you want to validate each day's performance.
    EXPECTED_IOPS_PER_SECOND = 30000
    EXPECTED_THROUGHPUT_MBPS = 1150

    read_iops_metric = "parallelstore.googleapis.com/instance/read_ops_count"
    throughput_metric = "parallelstore.googleapis.com/instance/transferred_byte_count"

    logger.info(f"===================================================================================")
    logger.info(f"Fetching Daily Peak Performance for Parallelstore Instance: {instance_id}")
    logger.info(f"Project: {project_id}")
    logger.info(f"Period: {start_date_overall.strftime('%Y-%m-%d')} to {end_date_overall.strftime('%Y-%m-%d')} (UTC)")
    logger.info(f"===================================================================================")

    all_daily_results_summary = [] # To store a summary if needed later

    current_day_iterator = start_date_overall
    while current_day_iterator <= end_date_overall:
        # Define the 24-hour window for the current day in UTC
        day_start_time = datetime(current_day_iterator.year, current_day_iterator.month, current_day_iterator.day, 0, 0, 0, tzinfo=timezone.utc)
        day_end_time = datetime(current_day_iterator.year, current_day_iterator.month, current_day_iterator.day, 23, 59, 59, tzinfo=timezone.utc)

        logger.info(f"--- Querying data for: {current_day_iterator.strftime('%Y-%m-%d')} ---")

        daily_peak_read_iops = None
        daily_peak_throughput_mbps = None
        day_met_iops_benchmark = None
        day_met_throughput_benchmark = None

        try:
            daily_peak_read_iops = fetch_metric(
                read_iops_metric, project_id, instance_id, day_start_time, day_end_time
            )
            daily_throughput_bytes_sec = fetch_metric(
                throughput_metric, project_id, instance_id, day_start_time, day_end_time
            )

            if daily_throughput_bytes_sec is not None:
                daily_peak_throughput_mbps = daily_throughput_bytes_sec / (1000**2) # MB/s

            logger.info(f"Results for {current_day_iterator.strftime('%Y-%m-%d')}:")
            logger.info(f"  Peak Read IOPS (rate): {daily_peak_read_iops} ops/sec")
            logger.info(f"  Peak Throughput (rate): {daily_peak_throughput_mbps} MBps")

            # Optional: Validate against benchmarks for the day
            if daily_peak_read_iops is not None:
                day_met_iops_benchmark = daily_peak_read_iops >= EXPECTED_IOPS_PER_SECOND
                if day_met_iops_benchmark:
                    logger.info(f"  IOPS Benchmark (Expected >= {EXPECTED_IOPS_PER_SECOND} ops/sec): PASSED")
                else:
                    logger.warning(f"  IOPS Benchmark (Expected >= {EXPECTED_IOPS_PER_SECOND} ops/sec): FAILED or BELOW THRESHOLD")
            else:
                logger.warning(f"  IOPS Benchmark: NO DATA for {current_day_iterator.strftime('%Y-%m-%d')}")

            if daily_peak_throughput_mbps is not None:
                day_met_throughput_benchmark = daily_peak_throughput_mbps >= EXPECTED_THROUGHPUT_MBPS
                if day_met_throughput_benchmark:
                    logger.info(f"  Throughput Benchmark (Expected >= {EXPECTED_THROUGHPUT_MBPS} MBps): PASSED")
                else:
                    logger.warning(f"  Throughput Benchmark (Expected >= {EXPECTED_THROUGHPUT_MBPS} MBps): FAILED or BELOW THRESHOLD")
            else:
                logger.warning(f"  Throughput Benchmark: NO DATA for {current_day_iterator.strftime('%Y-%m-%d')}")

        except Exception as e:
            logger.error(f"Could not retrieve or process metrics for {current_day_iterator.strftime('%Y-%m-%d')}: {e}", exc_info=True)
        
        all_daily_results_summary.append({
            "date": current_day_iterator.strftime('%Y-%m-%d'),
            "peak_read_iops_ops_sec": daily_peak_read_iops,
            "peak_throughput_mbps": daily_peak_throughput_mbps,
            "met_iops_benchmark": day_met_iops_benchmark,
            "met_throughput_benchmark": day_met_throughput_benchmark
        })

        current_day_iterator += timedelta(days=1)
        logger.info("-----------------------------------------------------------------------------------")


    logger.info("===================================================================================")
    logger.info("Daily performance fetching completed for the specified period.")
    logger.info("===================================================================================")
    
    # `all_daily_results_summary` list contains all collected data if you want to process it further
    # For example, write to a CSV or JSON file.
    # import json
    # with open('daily_performance_summary.json', 'w') as f:
    #     json.dump(all_daily_results_summary, f, indent=4)
    # logger.info("Daily performance summary saved to daily_performance_summary.json")

    return all_daily_results_summary


if __name__ == "__main__":
    logger.info("=====================================================================")
    logger.info("Starting Parallelstore Daily Metrics Retrieval Script...")
    logger.info(f"Current script execution time (UTC): {datetime.now(timezone.utc).isoformat()}")
    logger.info("Make sure the following are correctly set up before running:")
    logger.info("1. GCP Authentication: `gcloud auth application-default login` or `GOOGLE_APPLICATION_CREDENTIALS` env var.")
    logger.info(f"2. Project '{CONFIG['parallelstore']['project_id']}' has 'Cloud Monitoring API' enabled.")
    logger.info(f"3. Instance ID '{CONFIG['parallelstore']['instance_id']}' in CONFIG is the correct Parallelstore instance name.")
    logger.info("4. The authenticated principal has at least 'roles/monitoring.viewer' on the project.")
    logger.info("=====================================================================")

    # Define the overall period for which to fetch daily metrics
    # Start of March 1st, 2025, UTC
    period_start_date = datetime(2025, 3, 1, 0, 0, 0, tzinfo=timezone.utc)

    # Today's date (May 9th, 2025, based on simulated current time)
    # We want to include today in the query period.
    period_end_date = datetime(2025, 5, 9, 0, 0, 0, tzinfo=timezone.utc) # Ensure it's just the date part for the loop

    try:
        log_daily_performance_over_period(period_start_date, period_end_date)
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred during the script execution: {e}", exc_info=True)
        logger.critical("Please check authentication, permissions, API enablement, and instance identifiers.")
    finally:
        logger.info("=====================================================================")
        logger.info("Script execution finished.")
        logger.info("=====================================================================")
