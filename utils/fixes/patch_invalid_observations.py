from pathlib import Path

path = Path('components/control/report.py')
text = path.read_text(encoding='utf-8')
target = "        'successful_observations': valid_timestamps,\r\n        'valid_observations': valid_timestamps,  # Legacy alias\r\n        'valid_timestamps': valid_timestamps,  # Another legacy alias\r\n        'total_routes': len(link_data),  # Still track total rows for reference\r\n        'single_route_observations': single_alt_timestamps,\r\n"
replacement = "        'successful_observations': valid_timestamps,\r\n        'valid_observations': valid_timestamps,  # Legacy alias\r\n        'invalid_observations': total_timestamps - valid_timestamps,\r\n        'valid_timestamps': valid_timestamps,  # Another legacy alias\r\n        'total_routes': len(link_data),  # Still track total rows for reference\r\n        'single_route_observations': single_alt_timestamps,\r\n"
if target not in text:
    raise SystemExit('target snippet not found')
text = text.replace(target, replacement)
path.write_text(text, encoding='utf-8')
