#changes


import time
from google.cloud import monitoring_v3

# Create a client object for interacting with the API
client = monitoring_v3.MetricServiceClient()
# Create a request object
request = monitoring_v3.ListTimeSeriesRequest(...)
# Make the API call
response = client.list_time_series(request=request)

def validate_parallelstore_metrics():
    """
    Fetches and validates Parallelstore IOPS and throughput using Cloud Monitoring API
    """
    project_id = CONFIG["parallelstore"]["thomas_mig"]
    instance_id = CONFIG["parallelstore"]["persistenttest1"]
    region = CONFIG["parallelstore"]["us-central1-a"]

    # Expected benchmarks (update based on GCP docs)
    EXPECTED_IOPS = 30000
    EXPECTED_THROUGHPUT_MBPS = 1150  # 1.15 GiBps = 1150 MBps

    def fetch_metric(metric_type, instance_id):
        """
        Query Cloud Monitoring API for Parallelstore metrics and return the max value.
        """
        client = monitoring_v3.MetricServiceClient()
        project_name = f"projects/{project_id}"

        # Query last 30 minutes of data
        interval = monitoring_v3.TimeInterval(
            end_time={"seconds": int(time.time())},
            start_time={"seconds": int(time.time() - 1800)}  # Last 30 minutes
        )

        filter_str = f'metric.type="{metric_type}" AND resource.type = "parallelstore.googleapis.com/Instance" AND resource.label.instance_id="{instance_id}"'
        request = monitoring_v3.ListTimeSeriesRequest(
            name=project_name,
            filter=filter_str,
            interval=interval,
            view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        )

        result = client.list_time_series(request=request)

        # Extract all the values from the time series data
        values = [point.value.double_value for ts in result for point in ts.points]

        # Return the max value or None if no values found
        return max(values) if values else None

    # Fetch IOPS and throughput
    iops_metric = "parallelstore.googleapis.com/instance/read_ops_count"
    throughput_metric = "parallelstore.googleapis.com/instance/transferred_byte_count"
    actual_iops = fetch_metric(iops_metric, instance_id)
    actual_throughput_bytes = fetch_metric(throughput_metric, instance_id)

    # Convert throughput from bytes to MBps
    actual_throughput_mbps = (actual_throughput_bytes / 1024**2) if actual_throughput_bytes else None

    logger.info(f"Retrieved Parallelstore Metrics:")
    logger.info(f"Max IOPS: {actual_iops} (Expected: {EXPECTED_IOPS})")
    logger.info(f"Max Throughput: {actual_throughput_mbps} MBps (Expected: {EXPECTED_THROUGHPUT_MBPS} MBps)")

    # Validation against expected benchmarks
    assert actual_iops is not None and actual_iops >= EXPECTED_IOPS, f"IOPS too low: {actual_iops}"
    assert actual_throughput_mbps is not None and actual_throughput_mbps >= EXPECTED_THROUGHPUT_MBPS, f"Throughput too low: {actual_throughput_mbps} MBps"
    logger.info("Parallelstore performance meets GCP benchmarks!")