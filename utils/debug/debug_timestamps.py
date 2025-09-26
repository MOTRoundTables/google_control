"""Debug timestamp parsing issue"""
import pandas as pd
from datetime import datetime, timedelta

# Simulate the issue
csv_timestamps = ["29/06/2025 00:01", "29/06/2025 00:16", "29/06/2025 00:31"]
expected_start = datetime(2025, 6, 29, 0, 0, 0)

print("CSV timestamps (as parsed):")
parsed_csv = pd.to_datetime(csv_timestamps, dayfirst=True)
for ts in parsed_csv:
    print(f"  {ts}")

print(f"\nExpected timestamp: {expected_start}")

print(f"\nDo they match exactly? {expected_start in parsed_csv.values}")

# Show the fix - normalize to interval boundaries
interval_minutes = 15

def normalize_to_interval(ts, interval_minutes):
    """Round timestamp down to interval boundary"""
    minutes = ts.minute
    normalized_minutes = (minutes // interval_minutes) * interval_minutes
    return ts.replace(minute=normalized_minutes, second=0, microsecond=0)

print("\nAfter normalizing to 15-minute intervals:")
normalized_csv = [normalize_to_interval(ts, interval_minutes) for ts in parsed_csv]
for i, ts in enumerate(normalized_csv):
    print(f"  {csv_timestamps[i]} -> {ts}")

print(f"\nDoes expected match normalized? {expected_start in normalized_csv}")