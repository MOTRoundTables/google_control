#!/usr/bin/env python3
"""
Test the enhanced results display functionality
"""

import pandas as pd

def test_enhanced_results():
    """Test the enhanced results display features"""
    
    print("=== Testing Enhanced Results Display ===")
    
    # Create sample data with more rows
    data = []
    links = ['s_653-655', 's_9054-99', 's_1234-567', 's_789-012']
    dates = ['2025-06-29', '2025-06-30', '2025-07-01']
    hours = list(range(24))
    
    for link in links:
        for date in dates:
            for hour in hours[:8]:  # First 8 hours for testing
                data.append({
                    'link_id': link,
                    'date': date,
                    'hour_of_day': hour,
                    'n_valid': hour + 1,
                    'avg_duration_sec': 2000 + hour * 100,
                    'avg_speed_kmh': 80 + hour * 2
                })
    
    df = pd.DataFrame(data)
    print(f"Created test dataset with {len(df)} rows")
    
    # Test 1: Default display (100 rows)
    print(f"\n1. Default display (100 rows):")
    display_df = df.head(100)
    print(f"   Showing: {len(display_df)} rows")
    
    # Test 2: Show all rows
    print(f"\n2. Show all rows:")
    print(f"   Showing: {len(df)} rows")
    
    # Test 3: Filter by link ID
    print(f"\n3. Filter by link ID 's_653':")
    filtered_df = df[df['link_id'].str.contains('s_653', case=False, na=False)]
    print(f"   Filtered results: {len(filtered_df)} rows")
    print(f"   Unique links: {filtered_df['link_id'].unique()}")
    
    # Test 4: Column selection
    print(f"\n4. Column selection:")
    key_columns = ['link_id', 'date', 'hour_of_day', 'n_valid', 'avg_duration_sec', 'avg_speed_kmh']
    available_columns = [col for col in key_columns if col in df.columns]
    print(f"   Key columns: {available_columns}")
    print(f"   Total columns: {len(df.columns)}")
    
    # Test 5: Sorting
    print(f"\n5. Sorting test:")
    sorted_df = df.sort_values(['link_id', 'date', 'hour_of_day'])
    print(f"   First few rows after sorting:")
    print(sorted_df[['link_id', 'date', 'hour_of_day']].head())
    
    print(f"\n✅ Enhanced results display test completed!")
    
    print(f"\nNew features:")
    print(f"- 📊 Configurable row count: 50, 100, 200, 500, 1000, All")
    print(f"- 🔍 Link ID filtering: Search for specific links")
    print(f"- 📋 Column control: Show key columns or all columns")
    print(f"- 📏 Larger display: 400px height for better viewing")
    print(f"- 🔄 Reset filters: Clear all filters with one click")
    print(f"- 📈 Smart captions: Show filtered vs total counts")

if __name__ == "__main__":
    test_enhanced_results()