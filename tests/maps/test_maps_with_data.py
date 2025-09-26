"""
Test the Maps page with the provided test data files.
"""

import os
import pandas as pd
import geopandas as gpd
from components.maps.maps_page import MapsPageInterface

def test_data_files_exist():
    """Test that the provided data files exist."""
    
    test_files = {
        'shapefile': r"E:\google_agg\test_data\google_results_to_golan_17_8_25\google_results_to_golan_17_8_25.shp",
        'hourly_results': r"E:\google_agg\test_data\hourly_agg_all.csv",
        'weekly_results': r"E:\google_agg\test_data\weekly_hourly_profile_all.csv"
    }
    
    print("Checking test data files...")
    
    all_exist = True
    for file_type, file_path in test_files.items():
        if os.path.exists(file_path):
            print(f"✅ {file_type}: {file_path}")
        else:
            print(f"❌ {file_type}: {file_path} - NOT FOUND")
            all_exist = False
    
    return all_exist

def test_load_shapefile():
    """Test loading the shapefile."""
    
    shapefile_path = r"E:\google_agg\test_data\google_results_to_golan_17_8_25\google_results_to_golan_17_8_25.shp"
    
    if not os.path.exists(shapefile_path):
        print(f"❌ Shapefile not found: {shapefile_path}")
        return False
    
    try:
        # Load shapefile
        gdf = gpd.read_file(shapefile_path)
        
        print(f"✅ Shapefile loaded successfully")
        print(f"   - Features: {len(gdf):,}")
        print(f"   - CRS: {gdf.crs}")
        print(f"   - Columns: {list(gdf.columns)}")
        
        # Check required columns using the spatial manager validation
        from components.maps.spatial_data import SpatialDataManager
        spatial_manager = SpatialDataManager()
        
        try:
            # Handle column name variations (id vs Id) before validation
            if 'id' in gdf.columns and 'Id' not in gdf.columns:
                gdf = gdf.rename(columns={'id': 'Id'})
                print(f"   - Renamed 'id' column to 'Id'")
            
            is_valid, missing_cols = spatial_manager.validate_shapefile_schema(gdf)
            if is_valid:
                print(f"✅ All required columns present (with variations handled)")
            else:
                print(f"❌ Missing required columns: {missing_cols}")
                return False
        except Exception as e:
            print(f"❌ Schema validation error: {e}")
            return False
        
        # Show sample data
        print(f"   - Sample IDs: {gdf['Id'].head(3).tolist()}")
        print(f"   - Bounds: {gdf.total_bounds}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading shapefile: {e}")
        return False

def test_load_hourly_results():
    """Test loading the hourly results."""
    
    hourly_path = r"E:\google_agg\test_data\hourly_agg_all.csv"
    
    if not os.path.exists(hourly_path):
        print(f"❌ Hourly results not found: {hourly_path}")
        return False
    
    try:
        # Load hourly results
        df = pd.read_csv(hourly_path)
        
        print(f"✅ Hourly results loaded successfully")
        print(f"   - Records: {len(df):,}")
        print(f"   - Columns: {list(df.columns)}")
        
        # Check required columns (handle variations)
        required_cols = ['link_id', 'date', 'avg_duration_sec', 'avg_speed_kmh']
        hour_col_options = ['hour', 'hour_of_day']
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        # Check for hour column variations
        hour_col_found = any(col in df.columns for col in hour_col_options)
        if not hour_col_found:
            missing_cols.append('hour (or hour_of_day)')
        
        if missing_cols:
            print(f"❌ Missing required columns: {missing_cols}")
            return False
        else:
            print(f"✅ All required columns present (with variations handled)")
        
        # Show data summary
        if 'date' in df.columns:
            dates = pd.to_datetime(df['date'])
            print(f"   - Date range: {dates.min().date()} to {dates.max().date()}")
        
        if 'link_id' in df.columns:
            print(f"   - Unique links: {df['link_id'].nunique():,}")
        
        if 'hour' in df.columns:
            print(f"   - Hour range: {df['hour'].min()}-{df['hour'].max()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading hourly results: {e}")
        return False

def test_load_weekly_results():
    """Test loading the weekly results."""
    
    weekly_path = r"E:\google_agg\test_data\weekly_hourly_profile_all.csv"
    
    if not os.path.exists(weekly_path):
        print(f"❌ Weekly results not found: {weekly_path}")
        return False
    
    try:
        # Load weekly results
        df = pd.read_csv(weekly_path)
        
        print(f"✅ Weekly results loaded successfully")
        print(f"   - Records: {len(df):,}")
        print(f"   - Columns: {list(df.columns)}")
        
        # Check required columns (handle variations)
        required_cols = ['link_id']
        hour_col_options = ['hour', 'hour_of_day']
        duration_col_options = ['avg_duration_sec', 'avg_dur']
        speed_col_options = ['avg_speed_kmh', 'avg_speed']
        
        missing_cols = []
        
        # Check for hour column variations
        hour_col_found = any(col in df.columns for col in hour_col_options)
        if not hour_col_found:
            missing_cols.append('hour (or hour_of_day)')
        
        # Check for duration column variations
        duration_col_found = any(col in df.columns for col in duration_col_options)
        if not duration_col_found:
            missing_cols.append('avg_duration_sec (or avg_dur)')
        
        # Check for speed column variations
        speed_col_found = any(col in df.columns for col in speed_col_options)
        if not speed_col_found:
            missing_cols.append('avg_speed_kmh (or avg_speed)')
        
        if missing_cols:
            print(f"❌ Missing required columns: {missing_cols}")
            return False
        else:
            print(f"✅ All required columns present (with variations handled)")
        
        # Show data summary
        if 'link_id' in df.columns:
            print(f"   - Unique links: {df['link_id'].nunique():,}")
        
        if 'hour' in df.columns:
            print(f"   - Hour range: {df['hour'].min()}-{df['hour'].max()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading weekly results: {e}")
        return False

def test_data_join_compatibility():
    """Test that shapefile and results data can be joined."""
    
    shapefile_path = r"E:\google_agg\test_data\google_results_to_golan_17_8_25\google_results_to_golan_17_8_25.shp"
    hourly_path = r"E:\google_agg\test_data\hourly_agg_all.csv"
    
    if not (os.path.exists(shapefile_path) and os.path.exists(hourly_path)):
        print("❌ Required files not found for join test")
        return False
    
    try:
        # Load data
        gdf = gpd.read_file(shapefile_path)
        df = pd.read_csv(hourly_path)
        
        # Create shapefile link IDs (s_From-To pattern)
        shapefile_link_ids = set()
        for _, row in gdf.iterrows():
            link_id = f"s_{row['From']}-{row['To']}"
            shapefile_link_ids.add(link_id)
        
        # Get results link IDs
        results_link_ids = set(df['link_id'].unique())
        
        # Calculate join statistics
        matched_links = shapefile_link_ids.intersection(results_link_ids)
        missing_in_shapefile = results_link_ids - shapefile_link_ids
        missing_in_results = shapefile_link_ids - results_link_ids
        
        print(f"✅ Join compatibility analysis:")
        print(f"   - Shapefile links: {len(shapefile_link_ids):,}")
        print(f"   - Results links: {len(results_link_ids):,}")
        print(f"   - Matched links: {len(matched_links):,}")
        print(f"   - Missing in shapefile: {len(missing_in_shapefile):,}")
        print(f"   - Missing in results: {len(missing_in_results):,}")
        
        # Calculate match rate
        match_rate = len(matched_links) / len(shapefile_link_ids) * 100 if shapefile_link_ids else 0
        print(f"   - Match rate: {match_rate:.1f}%")
        
        if match_rate > 80:
            print(f"✅ Excellent join compatibility ({match_rate:.1f}%)")
        elif match_rate > 50:
            print(f"⚠️ Moderate join compatibility ({match_rate:.1f}%)")
        else:
            print(f"❌ Poor join compatibility ({match_rate:.1f}%)")
        
        return match_rate > 50  # Consider >50% as acceptable
        
    except Exception as e:
        print(f"❌ Error testing join compatibility: {e}")
        return False

def test_maps_interface_with_data():
    """Test the MapsPageInterface with the provided data."""
    
    try:
        # Create interface
        interface = MapsPageInterface()
        
        print(f"✅ MapsPageInterface created")
        print(f"   - Default shapefile: {interface.default_shapefile_path}")
        print(f"   - Default hourly: {interface.default_hourly_path}")
        print(f"   - Default weekly: {interface.default_weekly_path}")
        
        # Test auto-detection
        print(f"\n🔍 Testing auto-detection...")
        
        # Check if default files exist
        shapefile_exists = os.path.exists(interface.default_shapefile_path)
        hourly_exists = os.path.exists(interface.default_hourly_path)
        weekly_exists = os.path.exists(interface.default_weekly_path)
        
        print(f"   - Shapefile exists: {shapefile_exists}")
        print(f"   - Hourly exists: {hourly_exists}")
        print(f"   - Weekly exists: {weekly_exists}")
        
        if shapefile_exists and (hourly_exists or weekly_exists):
            print(f"✅ Auto-detection should work with provided data")
        else:
            print(f"⚠️ Some default files not found - manual loading required")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing MapsPageInterface: {e}")
        return False

def main():
    """Run all tests with the provided data."""
    
    print("=" * 60)
    print("TESTING MAPS PAGE WITH PROVIDED TEST DATA")
    print("=" * 60)
    
    tests = [
        ("Data Files Existence", test_data_files_exist),
        ("Shapefile Loading", test_load_shapefile),
        ("Hourly Results Loading", test_load_hourly_results),
        ("Weekly Results Loading", test_load_weekly_results),
        ("Data Join Compatibility", test_data_join_compatibility),
        ("Maps Interface with Data", test_maps_interface_with_data)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
        print()
    
    print("=" * 60)
    print(f"FINAL RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Maps page is ready to use with the provided data.")
        print("\n📋 USAGE INSTRUCTIONS:")
        print("1. Run: streamlit run app.py")
        print("2. Navigate to '🗺️ Maps' page")
        print("3. Click 'Auto-detect from Output' or load files manually")
        print("4. Access Map A (Hourly) and Map B (Weekly) tabs")
        return True
    else:
        print("⚠️ Some tests failed. Check the issues above.")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)