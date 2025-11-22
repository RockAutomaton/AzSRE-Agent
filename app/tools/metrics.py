import os
from datetime import timedelta, datetime
from azure.mgmt.monitor import MonitorManagementClient
from app.core.auth import get_credential


class AzureMetricsTool:
    def __init__(self):
        self.credential = get_credential()
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        if not subscription_id:
            raise ValueError("AZURE_SUBSCRIPTION_ID is not set")
            
        self.client = MonitorManagementClient(self.credential, subscription_id)

    def get_metric(self, resource_id: str, metric_name: str) -> str:
        """
        Fetches the average value of a metric for the last 15 minutes.
        """
        try:
            # Get timespan (last 15 mins)
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=15)
            timespan = f"{start_time.isoformat()}/{end_time.isoformat()}"

            metrics_data = self.client.metrics.list(
                resource_uri=resource_id,
                timespan=timespan,
                interval="PT1M",
                metricnames=metric_name,
                aggregation="Average"
            )

            if not metrics_data.value:
                return f"No metric data found for {metric_name}"

            # Extract the time series
            timeseries = metrics_data.value[0].timeseries
            if not timeseries or not timeseries[0].data:
                return f"No values recorded for {metric_name} in the last 15 mins"

            # Calculate simple average of the data points
            values = [d.average for d in timeseries[0].data if d.average is not None]
            if not values:
                return "Metric found but all values are None"
                
            avg_val = sum(values) / len(values)
            return f"Average {metric_name} over last 15m: {avg_val:.2f}"

        except Exception as e:
            return f"Error fetching metrics: {str(e)}"

