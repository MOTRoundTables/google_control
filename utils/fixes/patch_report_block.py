from pathlib import Path

path = Path('components/control/report.py')
text = path.read_text(encoding='utf-8')
old = "    # Get timestamp column name (handle both cases)\r\n    timestamp_col = 'timestamp' if 'timestamp' in link_data.columns else 'Timestamp'\r\n\r\n    # Group by timestamp to handle alternatives correctly\r\n    timestamp_groups = link_data.groupby(timestamp_col)\r\n"
new = "    # Get timestamp column name (handle both cases)\r\n    timestamp_col = 'timestamp' if 'timestamp' in link_data.columns else ('Timestamp' if 'Timestamp' in link_data.columns else None)\r\n    drop_temp_timestamp = False\r\n\r\n    if timestamp_col is None and not link_data.empty:\r\n        link_data = link_data.copy()\r\n        link_data['__synthetic_timestamp__'] = range(len(link_data))\r\n        timestamp_col = '__synthetic_timestamp__'\r\n        drop_temp_timestamp = True\r\n\r\n    # Group by timestamp to handle alternatives correctly\r\n    timestamp_groups = link_data.groupby(timestamp_col) if timestamp_col else []\r\n\r\n"
if old not in text:
    raise SystemExit('target block not found')
text = text.replace(old, new)
path.write_text(text, encoding='utf-8')
