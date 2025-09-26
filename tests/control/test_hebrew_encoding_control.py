"""
Test that the Hebrew encoding fix is properly applied in the control component.
"""

import pandas as pd
import tempfile
import os

# Create a test CSV with Hebrew text encoded in cp1255
test_data = """DataID,Name,DayInWeek,DayType
1,s_653-655,יום ג,יום חול
2,s_655-657,יום ד,יום חול
3,s_657-659,שבת,שבת
"""

# Write test data with cp1255 encoding
with tempfile.NamedTemporaryFile(mode='w', encoding='cp1255', suffix='.csv', delete=False) as f:
    f.write(test_data)
    temp_file = f.name

print(f"Created test file: {temp_file}")

# Test 1: Direct encoding detection
print("\n=== Test 1: Direct encoding detection ===")
try:
    import chardet
    with open(temp_file, 'rb') as f:
        raw_data = f.read()
    
    detected = chardet.detect(raw_data)
    print(f"chardet detected: {detected['encoding']} (confidence: {detected['confidence']:.2f})")
    
    # Test resolve_hebrew_encoding
    from components.processing.pipeline import resolve_hebrew_encoding
    resolved = resolve_hebrew_encoding(raw_data, detected['encoding'])
    print(f"Resolved encoding: {resolved}")
    
    if resolved.lower() in ['cp1255', 'windows-1255']:
        print("SUCCESS: Hebrew encoding correctly resolved to cp1255/windows-1255")
    else:
        print(f"ERROR: Expected cp1255 but got {resolved}")
        
except Exception as e:
    print(f"Error in test 1: {e}")

# Test 2: Load with resolved encoding
print("\n=== Test 2: Load with resolved encoding ===")
try:
    # Load with the resolved encoding
    df = pd.read_csv(temp_file, encoding='cp1255')
    print(f"Loaded DataFrame with {len(df)} rows")
    
    # Print raw bytes to check
    for val in df['DayInWeek']:
        print(f"  Value: {repr(val)}")
    
    # Check if Hebrew text is preserved (using repr to avoid encoding issues)
    first_val = df['DayInWeek'].iloc[0]
    if 'יום' in first_val or '\u05d9\u05d5\u05dd' in repr(first_val):
        print("SUCCESS: Hebrew text correctly preserved")
    else:
        print("ERROR: Hebrew text may be corrupted")
        
except Exception as e:
    print(f"Error in test 2: {e}")

# Test 3: Test with ISO-8859-7 (Greek) to see the problem
print("\n=== Test 3: Compare Greek vs Hebrew encoding ===")
try:
    # Try loading as Greek (wrong)
    try:
        df_greek = pd.read_csv(temp_file, encoding='ISO-8859-7')
        print(f"Greek encoding result: {repr(df_greek['DayInWeek'].iloc[0])}")
    except:
        print("Could not load as Greek")
    
    # Load correctly as Hebrew
    df_hebrew = pd.read_csv(temp_file, encoding='cp1255')
    print(f"Hebrew encoding result: {repr(df_hebrew['DayInWeek'].iloc[0])}")
    
except Exception as e:
    print(f"Error in test 3: {e}")

# Clean up
os.unlink(temp_file)
print(f"\nTest file cleaned up: {temp_file}")
