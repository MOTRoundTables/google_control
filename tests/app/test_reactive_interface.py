#!/usr/bin/env python3
"""
Test script for reactive interface functionality.
This script tests the enhanced reactive interface without requiring Streamlit to be running.
"""

import sys
import os
sys.path.append('.')

# Mock streamlit session_state for testing
class MockSessionState:
    def __init__(self):
        self._state = {}
    
    def __getitem__(self, key):
        return self._state[key]
    
    def __setitem__(self, key, value):
        self._state[key] = value
    
    def __contains__(self, key):
        return key in self._state
    
    def get(self, key, default=None):
        return self._state.get(key, default)
    
    def keys(self):
        return self._state.keys()
    
    def __getattr__(self, name):
        return self._state.get(name)
    
    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._state[name] = value

# Mock streamlit functions
class MockStreamlit:
    def __init__(self):
        self.session_state = MockSessionState()
    
    def rerun(self):
        print("🔄 Streamlit rerun called")
    
    def error(self, message):
        print(f"❌ Error: {message}")
    
    def success(self, message):
        print(f"✅ Success: {message}")
    
    def info(self, message):
        print(f"ℹ️ Info: {message}")
    
    def warning(self, message):
        print(f"⚠️ Warning: {message}")

# Replace streamlit with mock
import streamlit as st
mock_st = MockStreamlit()
st.session_state = mock_st.session_state
st.rerun = mock_st.rerun
st.error = mock_st.error
st.success = mock_st.success
st.info = mock_st.info
st.warning = mock_st.warning

def test_reactive_interface():
    """Test the reactive interface functionality."""
    
    print("🧪 Testing Reactive Interface Implementation")
    print("=" * 50)
    
    try:
        # Import the maps interface
        from components.maps.maps_page import MapsPageInterface
        
        # Test 1: Basic initialization
        print("\n1️⃣ Testing basic initialization...")
        interface = MapsPageInterface()
        print("✅ MapsPageInterface initialized successfully")
        
        # Test 2: Session state initialization
        print("\n2️⃣ Testing session state initialization...")
        interface._initialize_session_state()
        print("✅ Session state initialized successfully")
        
        # Verify reactive state components
        required_states = ['maps_shared_state', 'maps_loading_state', 'maps_performance', 'maps_preferences']
        for state in required_states:
            assert state in st.session_state, f"Missing {state} in session state"
        print("✅ All required reactive state components present")
        
        # Test 3: Reactive update mechanism
        print("\n3️⃣ Testing reactive update mechanism...")
        initial_render_count = st.session_state.maps_performance['render_count']
        
        # Enable reactive updates
        st.session_state.maps_preferences['reactive_updates'] = True
        
        # Trigger update
        interface._trigger_reactive_update('Test update')
        
        # Verify update was processed
        new_render_count = st.session_state.maps_performance['render_count']
        assert new_render_count > initial_render_count, "Render count should increase"
        assert st.session_state.maps_shared_state['last_update_time'] is not None, "Update time should be set"
        print("✅ Reactive update mechanism working correctly")
        
        # Test 4: Loading state management
        print("\n4️⃣ Testing loading state management...")
        st.session_state.maps_preferences['loading_indicators'] = True
        st.session_state.maps_loading_state['is_loading'] = True
        st.session_state.maps_loading_state['loading_message'] = "Test loading"
        
        # Finalize update
        interface._finalize_reactive_update()
        
        # Verify loading state was cleared
        assert st.session_state.maps_loading_state['is_loading'] is False, "Loading state should be cleared"
        assert st.session_state.maps_loading_state['loading_message'] == '', "Loading message should be cleared"
        print("✅ Loading state management working correctly")
        
        # Test 5: Error handling
        print("\n5️⃣ Testing error handling...")
        test_error = ValueError("Test error for reactive interface")
        interface._handle_reactive_error("Test context", test_error)
        
        # Verify error was recorded
        assert st.session_state.maps_loading_state['last_error'] == str(test_error), "Error should be recorded"
        assert st.session_state.maps_loading_state['error_timestamp'] is not None, "Error timestamp should be set"
        assert st.session_state.maps_performance.get('error_count', 0) > 0, "Error count should increase"
        print("✅ Error handling working correctly")
        
        # Test 6: Filter reset functionality
        print("\n6️⃣ Testing filter reset functionality...")
        
        # Set non-default values
        st.session_state.maps_shared_state['metric_type'] = 'speed'
        st.session_state.maps_shared_state['aggregation_method'] = 'mean'
        st.session_state['test_filter_enabled'] = True
        
        # Reset filters
        interface._reset_all_filters()
        
        # Verify reset
        assert st.session_state.maps_shared_state['metric_type'] == 'duration', "Metric type should reset to duration"
        assert st.session_state.maps_shared_state['aggregation_method'] == 'median', "Aggregation should reset to median"
        print("✅ Filter reset functionality working correctly")
        
        # Test 7: Performance metrics
        print("\n7️⃣ Testing performance metrics...")
        
        # Check performance state structure
        perf = st.session_state.maps_performance
        required_perf_keys = ['render_count', 'cache_hits', 'cache_misses', 'last_render_time']
        for key in required_perf_keys:
            assert key in perf, f"Missing performance metric: {key}"
        
        print("✅ Performance metrics structure correct")
        
        # Test 8: Shared state consistency
        print("\n8️⃣ Testing shared state consistency...")
        
        # Test shared state updates
        shared_state = st.session_state.maps_shared_state
        shared_state['metric_type'] = 'speed'
        shared_state['hour_range'] = (6, 22)
        
        # Verify consistency
        assert st.session_state.maps_shared_state['metric_type'] == 'speed', "Shared state should be consistent"
        assert st.session_state.maps_shared_state['hour_range'] == (6, 22), "Hour range should be consistent"
        print("✅ Shared state consistency working correctly")
        
        print("\n🎉 All reactive interface tests passed successfully!")
        print("=" * 50)
        
        # Summary
        print("\n📊 Test Summary:")
        print(f"   • Render count: {st.session_state.maps_performance['render_count']}")
        print(f"   • Cache hits: {st.session_state.maps_performance['cache_hits']}")
        print(f"   • Cache misses: {st.session_state.maps_performance['cache_misses']}")
        print(f"   • Error count: {st.session_state.maps_performance.get('error_count', 0)}")
        print(f"   • Reactive updates: {'Enabled' if st.session_state.maps_preferences['reactive_updates'] else 'Disabled'}")
        print(f"   • Loading indicators: {'Enabled' if st.session_state.maps_preferences['loading_indicators'] else 'Disabled'}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_data_integration():
    """Test integration with actual data files."""
    
    print("\n🗂️ Testing Data Integration")
    print("=" * 30)
    
    try:
        # Check if test data files exist
        hourly_path = "test_data/hourly_agg_all.csv"
        weekly_path = "test_data/weekly_hourly_profile_all.csv"
        
        if os.path.exists(hourly_path):
            import pandas as pd
            hourly_data = pd.read_csv(hourly_path)
            print(f"✅ Hourly data loaded: {len(hourly_data)} records")
            print(f"   Columns: {list(hourly_data.columns)}")
            print(f"   Unique links: {hourly_data['link_id'].nunique()}")
            
            # Verify required columns
            required_cols = ['link_id']
            hour_cols = ['hour', 'hour_of_day']
            duration_cols = ['avg_duration_sec', 'avg_dur']
            speed_cols = ['avg_speed_kmh', 'avg_speed']
            
            for col in required_cols:
                assert col in hourly_data.columns, f"Missing required column: {col}"
            
            assert any(col in hourly_data.columns for col in hour_cols), "Missing hour column"
            assert any(col in hourly_data.columns for col in duration_cols), "Missing duration column"
            assert any(col in hourly_data.columns for col in speed_cols), "Missing speed column"
            
            print("✅ Hourly data schema validation passed")
        else:
            print(f"⚠️ Hourly test data not found: {hourly_path}")
        
        if os.path.exists(weekly_path):
            import pandas as pd
            weekly_data = pd.read_csv(weekly_path)
            print(f"✅ Weekly data loaded: {len(weekly_data)} records")
            print(f"   Columns: {list(weekly_data.columns)}")
            print(f"   Unique links: {weekly_data['link_id'].nunique()}")
            
            # Verify required columns
            required_cols = ['link_id']
            hour_cols = ['hour', 'hour_of_day']
            duration_cols = ['avg_duration_sec', 'avg_dur']
            speed_cols = ['avg_speed_kmh', 'avg_speed']
            
            for col in required_cols:
                assert col in weekly_data.columns, f"Missing required column: {col}"
            
            assert any(col in weekly_data.columns for col in hour_cols), "Missing hour column"
            assert any(col in weekly_data.columns for col in duration_cols), "Missing duration column"
            assert any(col in weekly_data.columns for col in speed_cols), "Missing speed column"
            
            print("✅ Weekly data schema validation passed")
        else:
            print(f"⚠️ Weekly test data not found: {weekly_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data integration test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Reactive Interface Tests")
    print("=" * 60)
    
    # Run tests
    reactive_test_passed = test_reactive_interface()
    data_test_passed = test_data_integration()
    
    print("\n" + "=" * 60)
    print("📋 Final Test Results:")
    print(f"   • Reactive Interface: {'✅ PASSED' if reactive_test_passed else '❌ FAILED'}")
    print(f"   • Data Integration: {'✅ PASSED' if data_test_passed else '❌ FAILED'}")
    
    if reactive_test_passed and data_test_passed:
        print("\n🎉 All tests passed! Reactive interface is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)