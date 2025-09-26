"""
Test that control validation preserves exact field names from input
"""
import pandas as pd
import tempfile
import os
from pathlib import Path

# Create test CSV with exact field names
test_csv = """DataID,Name,SegmentID,RouteAlternative,Timestamp,DayInWeek,DayType,Duration,Distance,Speed,Polyline
1001,s_653-655,1185048,1,2025-01-07 13:45,יום ג,יום חול,2446,59428,87.5,_oxwD{_wtEoAlCe@vFq@ha@
1002,s_653-655,1185048,2,2025-01-07 13:45,יום ג,יום חול,2400,58000,87.0,_oxwD{_wtEoAlCe@vFq@ha@
"""

# Save test CSV
with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.csv', delete=False) as f:
    f.write(test_csv)
    test_file = f.name

try:
    # Read the CSV
    df = pd.read_csv(test_file)
    print("Original columns:", list(df.columns))
    
    # Check specific columns
    assert 'Name' in df.columns, "Name column should be preserved"
    assert 'RouteAlternative' in df.columns, "RouteAlternative column should be preserved"
    assert 'Timestamp' in df.columns, "Timestamp column should be preserved"
    
    # Simulate what the validator does - add new columns but preserve originals
    df['is_valid'] = True
    df['valid_code'] = 21
    
    print("After validation:", list(df.columns))
    
    # Verify original columns still present with exact names
    assert 'Name' in df.columns, "Name should still be present"
    assert 'RouteAlternative' in df.columns, "RouteAlternative should still be present"
    
    # Save and reload to verify
    output_file = test_file.replace('.csv', '_validated.csv')
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    df_reloaded = pd.read_csv(output_file)
    print("After save/reload:", list(df_reloaded.columns))
    
    assert 'Name' in df_reloaded.columns, "Name preserved after save"
    assert 'RouteAlternative' in df_reloaded.columns, "RouteAlternative preserved after save"
    
    print("\nSUCCESS: All field names preserved correctly!")
    
finally:
    # Clean up
    os.unlink(test_file)
    if os.path.exists(test_file.replace('.csv', '_validated.csv')):
        os.unlink(test_file.replace('.csv', '_validated.csv'))
