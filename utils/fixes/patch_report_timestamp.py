from pathlib import Path

path = Path('components/control/report.py')
text = path.read_text(encoding='utf-8')
marker = "    timestamp_col = 'timestamp' if 'timestamp' in link_data.columns else 'Timestamp'\n\n    if link_data.empty:\n        return {\n"
if marker not in text:
    raise SystemExit('marker not found')
replacement = "    timestamp_col = 'timestamp' if 'timestamp' in link_data.columns else ('Timestamp' if 'Timestamp' in link_data.columns else None)\n    drop_temp_timestamp = False\n\n    if timestamp_col is None and not link_data.empty:\n        link_data = link_data.copy()\n        link_data['__synthetic_timestamp__'] = range(len(link_data))\n        timestamp_col = '__synthetic_timestamp__'\n        drop_temp_timestamp = True\n\n    if link_data.empty:\n        return {\n"
text = text.replace(marker, replacement)
path.write_text(text, encoding='utf-8')
