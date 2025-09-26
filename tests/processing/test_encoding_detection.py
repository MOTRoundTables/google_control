from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent
PIPELINE_DIR = BASE_DIR / 'components' / 'processing'

# Add repository root and processing component directory to import path
sys.path.append(str(BASE_DIR))
sys.path.append(str(PIPELINE_DIR))

import pipeline  # type: ignore  # noqa: E402
import pandas as pd

detect_file_encoding = pipeline.detect_file_encoding
detect_csv_format = pipeline.detect_csv_format

def test_encoding_detection():
    """Test encoding detection with data_test_small.csv"""
    
    file_path = 'test_data/data_test_small.csv'
    
    print("Testing encoding detection...")
    
    # Test the detect_file_encoding function
    detected_encoding = detect_file_encoding(file_path)
    print(f"Detected encoding: {detected_encoding}")
    
    # Test CSV format detection
    csv_format = detect_csv_format(file_path)
    print(f"CSV format: {csv_format}")
    
    # Try reading with detected encoding
    print(f"\nTrying to read with detected encoding ({detected_encoding}):")
    try:
        df = pd.read_csv(file_path, encoding=detected_encoding, nrows=5)
        print(f"Success! Read {len(df)} rows")
        print("Sample timestamps:")
        if 'Timestamp' in df.columns:
            for i, ts in enumerate(df['Timestamp']):
                print(f"  {i}: '{ts}' (type: {type(ts)})")
        else:
            print("No Timestamp column found!")
            print(f"Columns: {list(df.columns)}")
    except Exception as e:
        print(f"Failed: {e}")
    
    # Compare with utf-8
    print(f"\nTrying to read with utf-8:")
    try:
        df_utf8 = pd.read_csv(file_path, encoding='utf-8', nrows=5)
        print(f"Success! Read {len(df_utf8)} rows")
        print("Sample timestamps:")
        if 'Timestamp' in df_utf8.columns:
            for i, ts in enumerate(df_utf8['Timestamp']):
                print(f"  {i}: '{ts}' (type: {type(ts)})")
    except Exception as e:
        print(f"Failed: {e}")

def test_control_file_detects_cp1255():
    """Ensure Hebrew control data is detected as cp1255 and preserves Hebrew characters."""

    control_dir = BASE_DIR / 'test_data' / 'control'
    control_files = [p for p in control_dir.iterdir() if p.name.startswith('original') and p.suffix == '.csv']
    assert control_files, "Control test CSV not found"

    control_path = control_files[0]
    detected_encoding = detect_file_encoding(str(control_path))
    assert detected_encoding.lower() in {'cp1255', 'windows-1255'}, (
        f"Expected cp1255 for Hebrew control data, got {detected_encoding}"
    )

    sample_df = pd.read_csv(control_path, encoding=detected_encoding, nrows=5)
    concatenated = ''.join(sample_df['DayInWeek'].astype(str).tolist())

    has_hebrew = any(0x0590 <= ord(ch) <= 0x05FF for ch in concatenated)
    assert has_hebrew, "Hebrew characters should be preserved in DayInWeek column"

if __name__ == "__main__":
    test_encoding_detection()
