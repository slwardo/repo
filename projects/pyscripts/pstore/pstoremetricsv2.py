import time
import logging
from datetime import datetime, timezone, timedelta
from google.cloud import monitoring_v3
from google.cloud.monitoring_v3.services.metric_service import pagers
import argparse

# --- Configuration Section ---
# Removed hardcoded project_id and instance_id
CONFIG = {
    "parallelstore": {
        "region": "us-central1"  # You can keep the region if it's still needed
    }
}

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('parallelstore_metrics_over_time.log', mode='a')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
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
    Queries the Google Cloud Monitoring API for a specific Parallelstore metric.
    It calculates the rate of the metric over 60-second intervals and returns the maximum
    rate observed within the specified query_start_time and query_end_time.
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

def log_daily_performance_over_period(start_date_overall: datetime, end_date_overall: datetime, project_id: str, instance_id: str):
    """
    Fetches and logs daily peak performance metrics (Read IOPS and Throughput)
    for the configured Parallelstore instance over a specified date range.
    It iterates day by day, queries metrics for each day, and logs the results.
    If no significant metrics are found for a day, detailed printing is skipped.
    """
    # Retrieve project and instance ID from the arguments.
    # project_id = CONFIG["parallelstore"]["project_id"] # Removed
    # instance_id = CONFIG["parallelstore"]["instance_id"] # Removed

    EXPECTED_IOPS_PER_SECOND = 30000
    EXPECTED_THROUGHPUT_MBPS = 1150

    read_iops_metric = "parallelstore.googleapis.com/instance/read_ops_count"
    throughput_metric = "parallelstore.googleapis.com/instance/transferred_byte_count"

    logger.info(f"===================================================================================")
    logger.info(f"Fetching Daily Peak Performance for Parallelstore Instance: {instance_id}")
    logger.info(f"Project: {project_id}")
    logger.info(f"Period: {start_date_overall.strftime('%Y-%m-%d')} to {end_date_overall.strftime('%Y-%m-%d')} (UTC)")
    logger.info(f"===================================================================================")

    all_daily_results_summary = []

    current_day_iterator = start_date_overall
    while current_day_iterator <= end_date_overall:
        day_start_time = datetime(current_day_iterator.year, current_day_iterator.month, current_day_iterator.day, 0, 0, 0, tzinfo=timezone.utc)
        day_end_time = datetime(current_day_iterator.year, current_day_iterator.month, current_day_iterator.day, 23, 59, 59, tzinfo=timezone.utc)

        logger.info(f"--- Querying data for: {current_day_iterator.strftime('%Y-%m-%d')} ---")

        daily_peak_read_iops = None
        daily_peak_throughput_mbps = None
        daily_throughput_bytes_sec = None
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
                daily_peak_throughput_mbps = daily_throughput_bytes_sec / (1000**2)

            if daily_peak_read_iops is None and daily_peak_throughput_mbps is None:
                logger.info(f"No significant performance metrics (IOPS or Throughput) found for {current_day_iterator.strftime('%Y-%m-%d')}.")
            else:
                logger.info(f"Results for {current_day_iterator.strftime('%Y-%m-%d')}:")
                if daily_peak_read_iops is not None:
                    logger.info(f"  Peak Read IOPS (rate): {daily_peak_read_iops:.2f} ops/sec")
                    day_met_iops_benchmark = daily_peak_read_iops >= EXPECTED_IOPS_PER_SECOND
                    if day_met_iops_benchmark:
                        logger.info(f"    IOPS Benchmark (Expected >= {EXPECTED_IOPS_PER_SECOND} ops/sec): PASSED")
                    else:
                        logger.warning(f"    IOPS Benchmark (Expected >= {EXPECTED_IOPS_PER_SECOND} ops/sec): FAILED or BELOW THRESHOLD")
                else:
                    logger.info(f"  Peak Read IOPS (rate): No data")
                    logger.warning(f"    IOPS Benchmark: NO DATA for {current_day_iterator.strftime('%Y-%m-%d')}")

                if daily_peak_throughput_mbps is not None:
                    logger.info(f"  Peak Throughput (rate): {daily_peak_throughput_mbps:.2f} MBps")
                    day_met_throughput_benchmark = daily_peak_throughput_mbps >= EXPECTED_THROUGHPUT_MBPS
                    if day_met_throughput_benchmark:
                        logger.info(f"    Throughput Benchmark (Expected >= {EXPECTED_THROUGHPUT_MBPS} MBps): PASSED")
                    else:
                        logger.warning(f"    Throughput Benchmark (Expected >= {EXPECTED_THROUGHPUT_MBPS} MBps): FAILED or BELOW THRESHOLD")
                else:
                    logger.info(f"  Peak Throughput (rate): No data")
                    logger.warning(f"    Throughput Benchmark: NO DATA for {current_day_iterator.strftime('%Y-%m-%d')}")

        except Exception as e:
            logger.error(f"Error retrieving or processing metrics for {current_day_iterator.strftime('%Y-%m-%d')}: {e}", exc_info=True)
        
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
    
    # --- Optional: Save summary to a file ---
    # import json
    # summary_file_name = f"daily_performance_summary_{start_date_overall.strftime('%Y%m%d')}_to_{end_date_overall.strftime('%Y%m%d')}.json"
    # try:
    #     with open(summary_file_name, 'w') as f:
    #         json.dump(all_daily_results_summary, f, indent=4)
    #     logger.info(f"Daily performance summary saved to {summary_file_name}")
    # except Exception as e:
    #     logger.error(f"Failed to save summary JSON file: {e}")
    # --- End Optional Save ---

    return all_daily_results_summary


# --- Main Execution Block ---
if __name__ == "__main__":
    logger.info("=====================================================================")
    logger.info("Starting Parallelstore Daily Metrics Retrieval Script...")
    logger.info(f"Current script execution time (UTC): {datetime.now(timezone.utc).isoformat()}")
    logger.info("Usage: python script.py --project_id <PROJECT_ID> --instance_id <INSTANCE_ID> --start_date YYYY-MM-DD [--end_date YYYY-MM-DD]")
    logger.info("=====================================================================")
    # Reminders for the user/client about necessary pre-requisites.
    logger.info("Make sure the following are correctly set up before running:")
    logger.info("1. GCP Authentication: Run `gcloud auth application-default login` OR set `GOOGLE_APPLICATION_CREDENTIALS` environment variable.")
    logger.info("2. 'Cloud Monitoring API' enabled in GCP.")
    logger.info("3. The authenticated principal (user or service account) has at least 'roles/monitoring.viewer' IAM permission on the project.")
    logger.info("=====================================================================")

    parser = argparse.ArgumentParser(
        description="Fetch daily peak performance metrics for a Parallelstore instance."
    )
    parser.add_argument(
        "--project_id",
        required=True,
        type=str,
        help="GCP Project ID.",
    )
    parser.add_argument(
        "--instance_id",
        required=True,
        type=str,
        help="Parallelstore Instance ID.",
    )
    parser.add_argument(
        "--start_date",
        required=True,
        type=str,
        help="Start date for the report (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end_date",
        type=str,
        default=None,
        help="End date for the report (YYYY-MM-DD). If not provided, it will default to today's date in UTC.",
    )
    args = parser.parse_args()

    try:
        period_start_date = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        logger.error(f"Invalid start date format: {args.start_date}. Please use YYYY-MM-DD format.")
        exit(1)
    if args.end_date:
        try:
            period_end_date = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
           logger.error(f"Invalid end date format: {args.end_date}. Please use YYYY-MM-DD format.")
           exit(1)
    else:
        period_end_date = datetime.now(timezone.utc)

    if period_start_date > period_end_date:
        logger.error(f"Error: The specified start date ({period_start_date.strftime('%Y-%m-%d')}) is after the end date ({period_end_date.strftime('%Y-%m-%d')}). Please correct the dates. Use --start_date and --end_date arguments. Also check the project_id and instance_id arguments.")
        exit(1)
    try:
        log_daily_performance_over_period(period_start_date, period_end_date, args.project_id, args.instance_id)
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred during the script execution: {e}", exc_info=True)
        logger.critical("Please check authentication, permissions, API enablement, and instance identifiers in the command line arguments.")
    finally:
        logger.info("=====================================================================")
        logger.info("Script execution finished.")
        logger.info("=====================================================================")

