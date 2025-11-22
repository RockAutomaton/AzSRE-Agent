import os
from datetime import timedelta, datetime, timezone
from azure.mgmt.monitor import MonitorManagementClient
from app.core.auth import get_credential


class AzureMetricsTool:
    def __init__(self):
        self.credential = get_credential()
        self.subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        if not self.subscription_id:
            raise ValueError("AZURE_SUBSCRIPTION_ID is not set")
            
        self.client = MonitorManagementClient(self.credential, self.subscription_id)

    def _format_value(self, metric_name: str, value: float) -> str:
        """
        Converts raw Azure metrics into human-readable units.
        """
        # 1. Percentage
        if "Percentage" in metric_name:
            return f"{value:.2f}%"

        # 2. Bytes -> GiB/MiB
        if "Bytes" in metric_name or "Memory" in metric_name:
            if value > 1024**3:
                return f"{value / (1024**3):.2f} GiB"
            return f"{value / (1024**2):.2f} MiB"
        
        # 3. Nanocores -> Cores
        if "NanoCores" in metric_name:
            return f"{value / 1_000_000_000:.4f} Cores"
            
        return f"{value:.2f}"

    def get_metric(self, resource_id: str, metric_name: str, minutes: int = 15) -> str:
        """
        Fetches the metric for the last N minutes.
        """
        try:
            # FIX: Use simple UTC Z-notation to avoid URL encoding issues with '+'
            now = datetime.now(timezone.utc)
            start = now - timedelta(minutes=minutes)
            
            # Format: YYYY-MM-DDTHH:MM:SSZ
            end_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
            timespan = f"{start_str}/{end_str}"

            # Fetch Metric
            metrics_data = self.client.metrics.list(
                resource_uri=resource_id,
                timespan=timespan,
                interval="PT1M",
                metricnames=metric_name,
                aggregation="Average"
            )

            if not metrics_data.value:
                return f"No data found for {metric_name}"

            timeseries = metrics_data.value[0].timeseries
            if not timeseries or not timeseries[0].data:
                return f"No recorded values for {metric_name}"

            # Extract valid data points
            data_points = [d for d in timeseries[0].data if d.average is not None]
            if not data_points:
                return f"{metric_name}: No data points (null)"
                
            # Statistics
            latest_val = data_points[-1].average
            avg_val = sum(d.average for d in data_points) / len(data_points)
            
            # Format
            fmt_latest = self._format_value(metric_name, latest_val)
            fmt_avg = self._format_value(metric_name, avg_val)
            
            return (f"{metric_name} (Last {minutes}m):\n"
                    f"  Current: {fmt_latest}\n"
                    f"  Average: {fmt_avg}")

        except Exception as e:
            return f"Error fetching {metric_name}: {str(e)}"
