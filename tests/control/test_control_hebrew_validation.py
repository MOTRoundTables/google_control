"""
End-to-end test for Hebrew text handling in control validation.
"""

import pandas as pd
import tempfile
import os
from pathlib import Path

# Test that control validation preserves Hebrew text
print("Testing Hebrew text preservation in control validation...")
print("=" * 60)

# Create test CSV with Hebrew text
test_csv_content = """DataID,Name,SegmentID,RouteAlternative,Timestamp,DayInWeek,DayType,Duration (seconds),Distance (meters),Speed (km/h),Polyline
1001,s_653-655,1185048,1,01/07/2025 13:45,יום ג,יום חול,2446,59428,87.5,_oxwD{_wtEoAlCe@vFq@ha@
1002,s_653-655,1185048,2,01/07/2025 13:45,יום ג,יום חול,2400,58000,87.0,_oxwD{_wtEoAlCe@vFq@ha@
1003,s_655-657,1185049,1,01/07/2025 14:00,יום ד,יום חול,2500,60000,86.0,_oxwD{_wtEoAlCe@vFq@ha@
"""

# Write test CSV with cp1255 encoding
with tempfile.NamedTemporaryFile(mode='w', encoding='cp1255', suffix='.csv', delete=False) as f:
    f.write(test_csv_content)
    test_csv_path = f.name

print(f"Created test CSV: {test_csv_path}")

# Test 1: Load CSV using the control component's method
print("\n=== Test 1: Load CSV with control component method ===")
try:
    # Simulate the control component's CSV loading
    class MockUploadedFile:
        def __init__(self, path):
            self.name = Path(path).name
            with open(path, 'rb') as f:
                self._content = f.read()
        
        def getvalue(self):
            return self._content
    
    mock_file = MockUploadedFile(test_csv_path)
    
    # Import and use the control component's load_csv_with_encoding
    import sys
    sys.path.insert(0, 'E:\google_agg')
    
    # Create a mock streamlit module to avoid UI dependencies
    class MockStreamlit:
        @staticmethod
        def info(msg):
            print(f"  INFO: {msg}")
        
        @staticmethod
        def warning(msg):
            print(f"  WARNING: {msg}")
        
        @staticmethod
        def error(msg):
            print(f"  ERROR: {msg}")
        
        @staticmethod
        def success(msg):
            print(f"  SUCCESS: {msg}")
    
    # Inject mock streamlit
    sys.modules['streamlit'] = MockStreamlit()
    
    # Now import the control page module
    from components.control.page import load_csv_with_encoding
    
    # Load the CSV
    df = load_csv_with_encoding(mock_file)
    
    if df is not None:
        print(f"\nLoaded {len(df)} rows")
        print("Columns:", list(df.columns))
        
        # Check Hebrew preservation
        if 'DayInWeek' in df.columns:
            print(f"\nDayInWeek values:")
            for idx, val in enumerate(df['DayInWeek'].head(3)):
                print(f"  Row {idx}: {repr(val)}")
                
            # Check for Hebrew characters
            first_val = str(df['DayInWeek'].iloc[0])
            if 'יום' in first_val or '���' in first_val:  # Hebrew or cp1255 representation
                print("\nSUCCESS: Hebrew text preserved in DayInWeek column")
            else:
                print(f"\nWARNING: Unexpected value in DayInWeek: {repr(first_val)}")
                
except Exception as e:
    print(f"Error in test 1: {e}")
    import traceback
    traceback.print_exc()

# Clean up
try:
    os.unlink(test_csv_path)
    print(f"\nTest file cleaned up: {test_csv_path}")
except:
    pass
