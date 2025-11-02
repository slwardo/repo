# Import necessary Python standard libraries
import time  # Used for time-related operations, though not directly in the final version's core logic after switching to datetime.
import logging # Used for logging information, warnings, and errors that occur during script execution.
from datetime import datetime, timezone, timedelta # Used for precise date and time manipulations, especially for defining query windows and iterating through days.
import argparse

# Import Google Cloud specific libraries
from google.cloud import monitoring_v3 # The Google Cloud Monitoring client library for interacting with the Monitoring API.
from google.cloud.monitoring_v3.services.metric_service import pagers # Specifically for handling paginated results from the API, if any.

# --- Configuration Section ---
# This section defines the core parameters for the script.
# TODO: CLIENT ACTION REQUIRED - These values MUST be verified and updated to match the client's specific GCP environment and Parallelstore instance.
CONFIG = {
    "parallelstore": {
        # project_id: The unique identifier for the Google Cloud Project where the Parallelstore instance is located.
        "project_id": "thomashk-mig",  # <<< CLIENT: Replace with your actual GCP Project ID.

        # instance_id: The specific name/ID of the Parallelstore instance to monitor.
        # IMPORTANT: This MUST be the actual Parallelstore instance name as it appears in the GCP Filestore/Parallelstore console.
        # It is NOT typically a PersistentVolumeClaim (PVC) name unless they happen to be identical by design.
        "instance_id": "instance-default", # <<< CLIENT: VERIFY and replace with your actual Parallelstore instance ID.

        # region: The GCP region where the Parallelstore instance is deployed (e.g., "us-central1", "europe-west1").
        # While not directly used in the current metric filter (as instance_id is usually globally unique within a project for Parallelstore),
        # it's good practice to have it if needed for other API calls or more specific filtering in the future.
        "region": "us-central1" # <<< CLIENT: Replace with the region of your Parallelstore instance.
    }
}

# --- Logging Setup ---
# This section configures how the script will record its operational messages.
# It sets up a logger that will output messages to both a file and the console.

# Get a logger instance. Using __name__ makes the logger's name the module's name.
logger = logging.getLogger(__name__)
# Set the minimum severity level of messages the logger will handle.
# logging.INFO means INFO, WARNING, ERROR, and CRITICAL messages will be processed.
# Change to logging.DEBUG for more detailed output, especially for API call details.
logger.setLevel(logging.INFO)

# Configure a File Handler: This will write log messages to a file.
# 'parallelstore_metrics_over_time.log' is the name of the log file.
# mode='a' means messages will be appended to the file if it exists; 'w' would overwrite.
file_handler = logging.FileHandler('parallelstore_metrics_over_time.log', mode='a')
# Define the format for log messages written to the file.
# %(asctime)s: Time the log record was created.
# %(name)s: Name of the logger.
# %(levelname)s: Textual representation of the log level (e.g., INFO, ERROR).
# %(message)s: The actual log message.
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter) # Apply this format to the file handler.
logger.addHandler(file_handler) # Add the configured file handler to the logger.

# Configure a Stream Handler: This will output log messages to the console (standard output).
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter) # Use the same formatter for console messages.
logger.addHandler(stream_handler) # Add the configured stream handler to the logger.
# --- End Logging Setup ---

def fetch_metric(
    metric_type: str,             # The full name of the metric to fetch (e.g., "parallelstore.googleapis.com/instance/read_ops_count").
    project_id_str: str,          # The GCP project ID.
    instance_id_str: str,         # The Parallelstore instance ID.
    query_start_time: datetime,   # The beginning of the time window for the query (as a datetime object, timezone-aware).
    query_end_time: datetime      # The end of the time window for the query (as a datetime object, timezone-aware).
) -> float | None:                # Returns the maximum metric value found (as a float) or None if no data or error.
    """
    Queries the Google Cloud Monitoring API for a specific Parallelstore metric.
    It calculates the rate of the metric over 60-second intervals and returns the maximum
    rate observed within the specified query_start_time and query_end_time.
    """
    # Create a client to interact with the Google Cloud Metric Service.
    client = monitoring_v3.MetricServiceClient()

    # Construct the full project resource name required by the API.
    project_name = f"projects/{project_id_str}"

    # Convert the human-readable datetime objects into Unix timestamps (seconds since epoch),
    # which is required by the Monitoring API for defining the time interval.
    start_time_seconds = int(query_start_time.timestamp())
    end_time_seconds = int(query_end_time.timestamp())

    # Define the time interval for the API query.
    # The API will look for metric data points that fall within [start_time, end_time].
    interval = monitoring_v3.types.TimeInterval(
        end_time={"seconds": end_time_seconds},
        start_time={"seconds": start_time_seconds}
    )

    # Define the aggregation strategy for processing the raw metric data.
    # This is crucial for converting raw counts (like operations or bytes) into meaningful rates (like IOPS or throughput).
    aggregation = monitoring_v3.types.Aggregation(
        # alignment_period: Specifies the time window for each aggregated data point.
        # Here, we align to 60-second periods. This means the API will create one aggregated point for each minute.
        alignment_period={"seconds": 60},

        # per_series_aligner: Defines how to aggregate data points within each alignment_period for each time series.
        # ALIGN_RATE: Calculates the rate of change. For a metric like 'read_ops_count', this will result in 'read_ops/second'.
        # For 'transferred_byte_count', it will be 'bytes/second'.
        per_series_aligner=monitoring_v3.types.Aggregation.Aligner.ALIGN_RATE,

        # cross_series_reducer: If the filter matches multiple time series (e.g., metrics from different zones for the same instance),
        # this defines how to combine them into a single time series.
        # REDUCE_MAX: Takes the maximum value across the different series for each alignment period.
        # For a single Parallelstore instance_id, there's typically only one series per metric type, making this less critical
        # but it's good practice to include a reducer.
        cross_series_reducer=monitoring_v3.types.Aggregation.Reducer.REDUCE_MAX
    )

    # Construct the filter string to select the specific metric data.
    # metric.type: The exact type of the metric.
    # resource.type: The type of GCP resource the metric is associated with.
    # resource.label.instance_id: Filters for the specific Parallelstore instance.
    filter_str = f'metric.type="{metric_type}" AND resource.type = "parallelstore.googleapis.com/Instance" AND resource.label.instance_id="{instance_id_str}"'

    # Create the API request object.
    request = monitoring_v3.types.ListTimeSeriesRequest(
        name=project_name,          # The project to query.
        filter=filter_str,          # The filter to select metrics.
        interval=interval,          # The time window for the query.
        view=monitoring_v3.types.ListTimeSeriesRequest.TimeSeriesView.FULL, # Requests all data (not just headers).
        aggregation=aggregation     # The aggregation strategy to apply.
    )

    # Log debug information about the API call being made.
    logger.debug(f"Fetching metric: {metric_type} for instance: {instance_id_str} in project: {project_id_str}")
    logger.debug(f"Query Window: {query_start_time.isoformat()} to {query_end_time.isoformat()}") # ISO format is a standard way to represent datetime.
    logger.debug(f"Filter: {filter_str}")
    logger.debug(f"Aggregation: Aligner=ALIGN_RATE, Alignment Period=60s, Reducer=REDUCE_MAX")

    try:
        # Execute the API call to list time series data.
        # This returns a "pager" object, which helps manage potentially large sets of results that are split into pages.
        results: pagers.ListTimeSeriesPager = client.list_time_series(request=request)

        # Store the processed metric values (rates).
        values = []
        # Iterate through each page of results (though for a single metric/instance, often just one page).
        for page in results.pages:
            # Each page contains time series data.
            for ts in page.time_series:
                # Each time series contains data points.
                for point in ts.points:
                    # After ALIGN_RATE, the metric value is typically a double (float).
                    if point.value.double_value is not None:
                        values.append(point.value.double_value)
                    # Fallback in case an integer value is returned, though less common with ALIGN_RATE.
                    elif point.value.int64_value is not None:
                         values.append(float(point.value.int64_value))

        # Log the raw rate values retrieved for debugging.
        logger.debug(f"Rate values for {metric_type} (from {query_start_time.strftime('%Y-%m-%d')} to {query_end_time.strftime('%Y-%m-%d')}): {values}")

        # Return the maximum rate found in the query window. If no values were found, return None.
        return max(values) if values else None
    except Exception as e:
        # Log any error that occurs during the API call or data processing.
        # exc_info=True includes traceback information in the log for detailed debugging.
        logger.error(f"Error fetching metric {metric_type} for {instance_id_str} over window {query_start_time.isoformat()} to {query_end_time.isoformat()}: {e}", exc_info=True)
        # Re-raise the exception so it can be handled by the calling function if necessary.
        raise

def log_daily_performance_over_period(start_date_overall: datetime, end_date_overall: datetime):
    """
    Fetches and logs daily peak performance metrics (Read IOPS and Throughput)
    for the configured Parallelstore instance over a specified date range.
    It iterates day by day, queries metrics for each day, and logs the results.
    If no significant metrics are found for a day, detailed printing is skipped.
    """
    # Retrieve project and instance ID from the global CONFIG.
    project_id = CONFIG["parallelstore"]["project_id"]
    instance_id = CONFIG["parallelstore"]["instance_id"]

    # Define expected performance benchmarks.
    # These are used for logging if a day's performance met expectations.
    # TODO: CLIENT - Adjust these benchmarks if needed for your specific performance targets.
    EXPECTED_IOPS_PER_SECOND = 30000  # Expected peak Read IOPS (operations per second).
    EXPECTED_THROUGHPUT_MBPS = 1150   # Expected peak Throughput in MegaBYTES per second (1 MB = 1,000,000 Bytes).

    # Define the metric names to be queried.
    read_iops_metric = "parallelstore.googleapis.com/instance/read_ops_count"
    throughput_metric = "parallelstore.googleapis.com/instance/transferred_byte_count" # This metric typically includes both read and write bytes.

    # Log a header for the overall reporting period.
    logger.info(f"===================================================================================")
    logger.info(f"Fetching Daily Peak Performance for Parallelstore Instance: {instance_id}")
    logger.info(f"Project: {project_id}")
    logger.info(f"Period: {start_date_overall.strftime('%Y-%m-%d')} to {end_date_overall.strftime('%Y-%m-%d')} (UTC)")
    logger.info(f"===================================================================================")

    # List to store a summary of results for each day. Can be used later for CSV/JSON export.
    all_daily_results_summary = []

    # Initialize the iterator for the loop to the start date of the overall period.
    current_day_iterator = start_date_overall
    # Loop through each day from the start_date_overall to end_date_overall (inclusive).
    while current_day_iterator <= end_date_overall:
        # Define the 24-hour window for the current day in UTC.
        # Start of the day (00:00:00 UTC).
        day_start_time = datetime(current_day_iterator.year, current_day_iterator.month, current_day_iterator.day, 0, 0, 0, tzinfo=timezone.utc)
        # End of the day (23:59:59 UTC). This defines an inclusive end for the API query.
        day_end_time = datetime(current_day_iterator.year, current_day_iterator.month, current_day_iterator.day, 23, 59, 59, tzinfo=timezone.utc)

        # Log which day's data is being queried.
        logger.info(f"--- Querying data for: {current_day_iterator.strftime('%Y-%m-%d')} ---")

        # Initialize metric variables for the current day.
        daily_peak_read_iops = None
        daily_peak_throughput_mbps = None
        daily_throughput_bytes_sec = None # Intermediate variable for raw bytes/sec from API.
        day_met_iops_benchmark = None     # Flag to track if IOPS benchmark was met.
        day_met_throughput_benchmark = None # Flag to track if Throughput benchmark was met.

        try:
            # Fetch the peak read IOPS rate for the current day.
            daily_peak_read_iops = fetch_metric(
                read_iops_metric, project_id, instance_id, day_start_time, day_end_time
            )
            # Fetch the peak throughput rate (in bytes/second) for the current day.
            daily_throughput_bytes_sec = fetch_metric(
                throughput_metric, project_id, instance_id, day_start_time, day_end_time
            )

            # Convert throughput from bytes/second to MegaBYTES/second if data was found.
            # 1 MB = 1,000,000 Bytes. If MiB (1024*1024) is preferred, adjust the divisor.
            if daily_throughput_bytes_sec is not None:
                daily_peak_throughput_mbps = daily_throughput_bytes_sec / (1000**2)

            # Conditional printing: Only print detailed results if at least one significant metric was found for the day.
            if daily_peak_read_iops is None and daily_peak_throughput_mbps is None:
                # If both IOPS and Throughput data are missing, log a single summary line.
                logger.info(f"No significant performance metrics (IOPS or Throughput) found for {current_day_iterator.strftime('%Y-%m-%d')}.")
            else:
                # If at least one metric has data, proceed to log detailed results.
                logger.info(f"Results for {current_day_iterator.strftime('%Y-%m-%d')}:")

                # Log Read IOPS results and benchmark comparison.
                if daily_peak_read_iops is not None:
                    logger.info(f"  Peak Read IOPS (rate): {daily_peak_read_iops:.2f} ops/sec") # Format to 2 decimal places.
                    day_met_iops_benchmark = daily_peak_read_iops >= EXPECTED_IOPS_PER_SECOND
                    if day_met_iops_benchmark:
                        logger.info(f"    IOPS Benchmark (Expected >= {EXPECTED_IOPS_PER_SECOND} ops/sec): PASSED")
                    else:
                        logger.warning(f"    IOPS Benchmark (Expected >= {EXPECTED_IOPS_PER_SECOND} ops/sec): FAILED or BELOW THRESHOLD")
                else:
                    # Log if Read IOPS data was specifically missing.
                    logger.info(f"  Peak Read IOPS (rate): No data")
                    logger.warning(f"    IOPS Benchmark: NO DATA for {current_day_iterator.strftime('%Y-%m-%d')}")

                # Log Throughput results and benchmark comparison.
                if daily_peak_throughput_mbps is not None:
                    logger.info(f"  Peak Throughput (rate): {daily_peak_throughput_mbps:.2f} MBps") # Format to 2 decimal places.
                    day_met_throughput_benchmark = daily_peak_throughput_mbps >= EXPECTED_THROUGHPUT_MBPS
                    if day_met_throughput_benchmark:
                        logger.info(f"    Throughput Benchmark (Expected >= {EXPECTED_THROUGHPUT_MBPS} MBps): PASSED")
                    else:
                        logger.warning(f"    Throughput Benchmark (Expected >= {EXPECTED_THROUGHPUT_MBPS} MBps): FAILED or BELOW THRESHOLD")
                else:
                    # Log if Throughput data was specifically missing.
                    logger.info(f"  Peak Throughput (rate): No data")
                    logger.warning(f"    Throughput Benchmark: NO DATA for {current_day_iterator.strftime('%Y-%m-%d')}")

        except Exception as e:
            # Log any error encountered during metric fetching or processing for the current day.
            # This allows the loop to continue to the next day if one day fails.
            logger.error(f"Error retrieving or processing metrics for {current_day_iterator.strftime('%Y-%m-%d')}: {e}", exc_info=True)
            # Metric values will likely remain None, and the conditional logging above will handle this.
        
        # Append the results for the current day to the summary list.
        # This happens regardless of whether data was found or an error occurred, to maintain a complete daily record.
        all_daily_results_summary.append({
            "date": current_day_iterator.strftime('%Y-%m-%d'),
            "peak_read_iops_ops_sec": daily_peak_read_iops,
            "peak_throughput_mbps": daily_peak_throughput_mbps,
            "met_iops_benchmark": day_met_iops_benchmark,
            "met_throughput_benchmark": day_met_throughput_benchmark
        })

        # Move to the next day.
        current_day_iterator += timedelta(days=1)
        # Log a separator for readability between days.
        logger.info("-----------------------------------------------------------------------------------")


    # Log a footer indicating the completion of the daily fetching process.
    logger.info("===================================================================================")
    logger.info("Daily performance fetching completed for the specified period.")
    logger.info("===================================================================================")
    
    # --- Optional: Save summary to a file ---
    # The `all_daily_results_summary` list contains all collected data.
    # You can uncomment the following lines to save this data to a JSON file for further analysis or reporting.
    # import json
    # summary_file_name = f"daily_performance_summary_{start_date_overall.strftime('%Y%m%d')}_to_{end_date_overall.strftime('%Y%m%d')}.json"
    # try:
    #     with open(summary_file_name, 'w') as f:
    #         json.dump(all_daily_results_summary, f, indent=4) # indent=4 makes the JSON file human-readable.
    #     logger.info(f"Daily performance summary saved to {summary_file_name}")
    # except Exception as e:
    #     logger.error(f"Failed to save summary JSON file: {e}")
    # --- End Optional Save ---

    return all_daily_results_summary


# --- Main Execution Block ---
# This block is executed when the script is run directly (not imported as a module).
if __name__ == "__main__":
    import argparse
    logger.info("=====================================================================")
    logger.info("Starting Parallelstore Daily Metrics Retrieval Script...")
    logger.info(f"Current script execution time (UTC): {datetime.now(timezone.utc).isoformat()}") # Log current time in UTC.
    logger.info("Usage: python script.py --start_date YYYY-MM-DD [--end_date YYYY-MM-DD]")
    logger.info("=====================================================================")
    # Reminders for the user/client about necessary pre-requisites.
    logger.info("Make sure the following are correctly set up before running:")
    logger.info("1. GCP Authentication: Run `gcloud auth application-default login` OR set `GOOGLE_APPLICATION_CREDENTIALS` environment variable.")
    logger.info(f"2. Project '{CONFIG['parallelstore']['project_id']}' has 'Cloud Monitoring API' enabled in GCP.")
    logger.info(f"3. Instance ID '{CONFIG['parallelstore']['instance_id']}' in CONFIG is the correct Parallelstore instance name.")
    logger.info("4. The authenticated principal (user or service account) has at least 'roles/monitoring.viewer' IAM permission on the project.")
    logger.info("=====================================================================")

    parser = argparse.ArgumentParser(
        description="Fetch daily peak performance metrics for a Parallelstore instance."
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
        logger.error(f"Error: The specified start date ({period_start_date.strftime('%Y-%m-%d')}) is after the end date ({period_end_date.strftime('%Y-%m-%d')}). Please correct the dates. Use --start_date and --end_date arguments.")
        exit(1)
    try:
        log_daily_performance_over_period(period_start_date, period_end_date)
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred during the script execution: {e}", exc_info=True)
        logger.critical("Please check authentication, permissions, API enablement, and instance identifiers in the CONFIG section.")
    finally:
        logger.info("=====================================================================")
        logger.info("Script execution finished.")
        logger.info("=====================================================================")
