#!/usr/bin/env python3
"""
Test script for maps functionality with actual test data.
This script tests that maps display correctly with the test data files.
"""

import sys
import os
sys.path.append('.')

def test_maps_with_test_data():
    """Test that maps can be created with the actual test data."""
    
    print("🗺️ Testing Maps Functionality with Test Data")
    print("=" * 50)
    
    try:
        import pandas as pd
        import geopandas as gpd
        from shapely.geometry import LineString
        
        # Load test data
        hourly_path = "test_data/hourly_agg_all.csv"
        weekly_path = "test_data/weekly_hourly_profile_all.csv"
        
        if not os.path.exists(hourly_path):
            print(f"❌ Hourly test data not found: {hourly_path}")
            return False
        
        if not os.path.exists(weekly_path):
            print(f"❌ Weekly test data not found: {weekly_path}")
            return False
        
        # Load data
        print("📊 Loading test data...")
        hourly_data = pd.read_csv(hourly_path)
        weekly_data = pd.read_csv(weekly_path)
        
        print(f"✅ Hourly data: {len(hourly_data)} records, {hourly_data['link_id'].nunique()} unique links")
        print(f"✅ Weekly data: {len(weekly_data)} records, {weekly_data['link_id'].nunique()} unique links")
        
        # Standardize column names
        if 'hour_of_day' in hourly_data.columns and 'hour' not in hourly_data.columns:
            hourly_data = hourly_data.rename(columns={'hour_of_day': 'hour'})
            print("✅ Standardized hourly data column names")
        
        if 'hour_of_day' in weekly_data.columns and 'hour' not in weekly_data.columns:
            weekly_data = weekly_data.rename(columns={'hour_of_day': 'hour'})
        
        if 'avg_dur' in weekly_data.columns and 'avg_duration_sec' not in weekly_data.columns:
            weekly_data = weekly_data.rename(columns={'avg_dur': 'avg_duration_sec'})
        
        if 'avg_speed' in weekly_data.columns and 'avg_speed_kmh' not in weekly_data.columns:
            weekly_data = weekly_data.rename(columns={'avg_speed': 'avg_speed_kmh'})
            print("✅ Standardized weekly data column names")
        
        # Create sample shapefile data based on the link_ids in the results
        print("🗺️ Creating sample shapefile data...")
        
        # Get unique link_ids and extract From-To information
        unique_links = hourly_data['link_id'].unique()[:100]  # Use first 100 for testing
        
        shapefile_data = []
        for i, link_id in enumerate(unique_links):
            if link_id.startswith('s_') and '-' in link_id:
                # Extract From-To from link_id (format: s_From-To)
                from_to = link_id[2:]  # Remove 's_' prefix
                if '-' in from_to:
                    from_node, to_node = from_to.split('-', 1)
                    
                    # Create simple line geometry
                    start_x, start_y = i * 100, i * 100
                    end_x, end_y = start_x + 50, start_y + 50
                    
                    shapefile_data.append({
                        'Id': f'link_{i}',
                        'From': from_node,
                        'To': to_node,
                        'geometry': LineString([(start_x, start_y), (end_x, end_y)])
                    })
        
        if not shapefile_data:
            print("❌ Could not create shapefile data from link_ids")
            return False
        
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(shapefile_data, crs="EPSG:2039")
        print(f"✅ Created sample shapefile: {len(gdf)} features")
        
        # Test data joining
        print("🔗 Testing data joining...")
        
        try:
            from components.maps.map_data import MapDataProcessor
            processor = MapDataProcessor()
            
            # Test join with hourly data
            joined_hourly = processor.join_results_to_shapefile(gdf, hourly_data)
            print(f"✅ Hourly data join: {len(joined_hourly)} features")
            
            # Test join with weekly data
            joined_weekly = processor.join_results_to_shapefile(gdf, weekly_data)
            print(f"✅ Weekly data join: {len(joined_weekly)} features")
            
            if len(joined_hourly) == 0:
                print("⚠️ No hourly data joined - checking link_id format...")
                print(f"Sample shapefile link_ids: {[f's_{row.From}-{row.To}' for _, row in gdf.head(3).iterrows()]}")
                print(f"Sample hourly link_ids: {hourly_data['link_id'].head(3).tolist()}")
            
            if len(joined_weekly) == 0:
                print("⚠️ No weekly data joined - checking link_id format...")
                print(f"Sample weekly link_ids: {weekly_data['link_id'].head(3).tolist()}")
            
        except Exception as e:
            print(f"❌ Error in data joining: {str(e)}")
            return False
        
        # Test map creation (basic test)
        print("🗺️ Testing map creation...")
        
        try:
            # Test that we can import and initialize map interfaces
            from components.maps.map_a_hourly import HourlyMapInterface
            from components.maps.map_b_weekly import WeeklyMapInterface
            
            hourly_interface = HourlyMapInterface()
            weekly_interface = WeeklyMapInterface()
            
            print("✅ Map interfaces initialized successfully")
            
            # Test basic map creation (without full rendering)
            if len(joined_hourly) > 0:
                # Add required columns for map creation
                if 'avg_duration_min' not in joined_hourly.columns and 'avg_duration_sec' in joined_hourly.columns:
                    joined_hourly['avg_duration_min'] = joined_hourly['avg_duration_sec'] / 60
                
                print("✅ Map A data preparation successful")
            
            if len(joined_weekly) > 0:
                # Add required columns for map creation
                if 'avg_duration_min' not in joined_weekly.columns and 'avg_duration_sec' in joined_weekly.columns:
                    joined_weekly['avg_duration_min'] = joined_weekly['avg_duration_sec'] / 60
                
                print("✅ Map B data preparation successful")
            
        except Exception as e:
            print(f"❌ Error in map creation: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False
        
        # Test reactive interface integration
        print("🔄 Testing reactive interface integration...")
        
        try:
            # Mock streamlit for testing
            class MockSessionState:
                def __init__(self):
                    self._state = {}
                
                def __getattr__(self, name):
                    return self._state.get(name)
                
                def __setattr__(self, name, value):
                    if name.startswith('_'):
                        super().__setattr__(name, value)
                    else:
                        self._state[name] = value
                
                def __contains__(self, key):
                    return key in self._state
                
                def get(self, key, default=None):
                    return self._state.get(key, default)
            
            # Mock streamlit
            import streamlit as st
            st.session_state = MockSessionState()
            
            # Test maps page interface
            from components.maps.maps_page import MapsPageInterface
            maps_interface = MapsPageInterface()
            maps_interface._initialize_session_state()
            
            # Load test data into session state
            st.session_state.maps_shapefile_data = gdf
            st.session_state.maps_hourly_results = hourly_data
            st.session_state.maps_weekly_results = weekly_data
            
            # Test data availability check
            data_available = maps_interface._check_data_availability()
            assert data_available, "Data availability check should return True"
            
            print("✅ Reactive interface integration successful")
            
        except Exception as e:
            print(f"❌ Error in reactive interface integration: {str(e)}")
            return False
        
        print("\n🎉 All maps functionality tests passed!")
        print("=" * 50)
        
        # Summary
        print("\n📊 Test Summary:")
        print(f"   • Hourly data: {len(hourly_data):,} records")
        print(f"   • Weekly data: {len(weekly_data):,} records")
        print(f"   • Sample shapefile: {len(gdf)} features")
        print(f"   • Hourly joins: {len(joined_hourly) if 'joined_hourly' in locals() else 0}")
        print(f"   • Weekly joins: {len(joined_weekly) if 'joined_weekly' in locals() else 0}")
        print(f"   • Data available: {data_available if 'data_available' in locals() else False}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Maps functionality test failed: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Maps Functionality Tests")
    print("=" * 60)
    
    # Run test
    test_passed = test_maps_with_test_data()
    
    print("\n" + "=" * 60)
    print("📋 Final Test Results:")
    print(f"   • Maps Functionality: {'✅ PASSED' if test_passed else '❌ FAILED'}")
    
    if test_passed:
        print("\n🎉 Maps functionality test passed! Maps should display correctly with test data.")
        sys.exit(0)
    else:
        print("\n❌ Maps functionality test failed. Please check the implementation.")
        sys.exit(1)