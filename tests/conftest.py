"""
Pytest configuration and fixtures for map visualization tests.
"""

import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Point
import numpy as np
from datetime import date, datetime, timedelta
import tempfile
import os
from pathlib import Path


@pytest.fixture
def sample_shapefile_data():
    """Create sample shapefile data for testing."""
    # Create sample LineString geometries
    geometries = [
        LineString([(0, 0), (1, 1)]),
        LineString([(1, 1), (2, 2)]),
        LineString([(2, 2), (3, 3)]),
        LineString([(0, 1), (1, 2)]),
        LineString([(1, 2), (2, 3)])
    ]
    
    data = {
        'Id': ['L001', 'L002', 'L003', 'L004', 'L005'],
        'From': ['N001', 'N002', 'N003', 'N001', 'N002'],
        'To': ['N002', 'N003', 'N004', 'N003', 'N004'],
        'geometry': geometries
    }
    
    gdf = gpd.GeoDataFrame(data, crs="EPSG:2039")
    return gdf


@pytest.fixture
def sample_results_data():
    """Create sample results data for testing."""
    # Create data for multiple dates and hours
    dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(5)]
    hours = list(range(24))
    link_ids = ['s_N001-N002', 's_N002-N003', 's_N003-N004', 's_N001-N003', 's_N002-N004']
    
    data = []
    for link_id in link_ids:
        for d in dates:
            for h in hours:
                # Generate realistic traffic data
                base_speed = np.random.normal(40, 10)  # Base speed around 40 km/h
                base_duration = np.random.normal(120, 30)  # Base duration around 2 minutes
                
                # Add time-of-day variation
                if 7 <= h <= 9 or 17 <= h <= 19:  # Rush hours
                    speed_factor = 0.7
                    duration_factor = 1.5
                else:
                    speed_factor = 1.0
                    duration_factor = 1.0
                
                data.append({
                    'link_id': link_id,
                    'date': d.strftime('%Y-%m-%d'),
                    'hour': h,
                    'avg_speed_kmh': max(10, base_speed * speed_factor),
                    'avg_duration_sec': max(30, base_duration * duration_factor),
                    'n_valid': np.random.randint(5, 50)
                })
    
    return pd.DataFrame(data)


@pytest.fixture
def sample_joined_data(sample_shapefile_data, sample_results_data):
    """Create sample joined data for testing."""
    # Simple join for testing
    joined_data = sample_shapefile_data.copy()
    
    # Add some sample results data
    joined_data['avg_speed_kmh'] = [35.5, 42.1, 38.9, 41.2, 36.8]
    joined_data['avg_duration_sec'] = [180, 150, 165, 155, 175]
    joined_data['n_valid'] = [25, 30, 20, 35, 28]
    joined_data['date'] = '2025-01-01'
    joined_data['hour'] = 8
    
    return joined_data


@pytest.fixture
def temp_directory():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_config():
    """Create sample configuration for testing."""
    return {
        "map_symbology": {
            "duration": {
                "palette": "RdYlGn_r",
                "classification": "quantiles",
                "n_classes": 5,
                "outlier_caps": [2, 98],
                "width_scale": [1, 8],
                "opacity_scale": [0.3, 1.0]
            },
            "speed": {
                "palette": "RdYlGn",
                "classification": "quantiles",
                "n_classes": 5,
                "outlier_caps": [2, 98],
                "width_scale": [1, 8],
                "opacity_scale": [0.3, 1.0]
            }
        },
        "thresholds": {
            "free_flow_speed_kmh": 50,
            "max_acceptable_duration_sec": 1800,
            "min_observations_for_confidence": 10
        }
    }


@pytest.fixture
def mock_data_bounds():
    """Create mock data bounds for testing controls."""
    return {
        'min_date': date(2025, 1, 1),
        'max_date': date(2025, 1, 31),
        'min_hour': 0,
        'max_hour': 23,
        'length_m': {'min': 100, 'max': 5000},
        'avg_speed_kmh': {'min': 10, 'max': 80},
        'avg_duration_sec': {'min': 30, 'max': 600}
    }


@pytest.fixture
def sample_filter_config():
    """Create sample filter configuration for testing."""
    return {
        'temporal': {
            'date_range': (date(2025, 1, 1), date(2025, 1, 31)),
            'hour_range': (7, 19)
        },
        'attributes': {
            'avg_speed_kmh': {
                'operator': 'above',
                'value': 30
            },
            'length_m': {
                'operator': 'between',
                'value': (100, 2000)
            }
        }
    }


# Test data generators
class TestDataGenerator:
    """Utility class for generating test data."""
    
    @staticmethod
    def create_large_network(n_links: int = 1000) -> gpd.GeoDataFrame:
        """Create large network for performance testing."""
        geometries = []
        ids = []
        froms = []
        tos = []
        
        for i in range(n_links):
            # Create random LineString
            x1, y1 = np.random.uniform(0, 100, 2)
            x2, y2 = np.random.uniform(0, 100, 2)
            geometries.append(LineString([(x1, y1), (x2, y2)]))
            
            ids.append(f'L{i:06d}')
            froms.append(f'N{i:06d}')
            tos.append(f'N{(i+1):06d}')
        
        data = {
            'Id': ids,
            'From': froms,
            'To': tos,
            'geometry': geometries
        }
        
        return gpd.GeoDataFrame(data, crs="EPSG:2039")
    
    @staticmethod
    def create_results_with_quality_issues(n_records: int = 1000) -> pd.DataFrame:
        """Create results data with various quality issues for testing."""
        data = []
        
        for i in range(n_records):
            # Some records with quality issues
            if i % 10 == 0:  # 10% with zero/negative speed
                speed = 0 if i % 20 == 0 else -5
            elif i % 15 == 0:  # Some with extreme values
                speed = 200  # Unrealistic high speed
            else:
                speed = np.random.normal(40, 15)
            
            if i % 12 == 0:  # Some with extreme durations
                duration = 3600  # 1 hour - unrealistic
            elif i % 8 == 0:  # Some with zero duration
                duration = 0
            else:
                duration = np.random.normal(120, 40)
            
            data.append({
                'link_id': f's_N{i:06d}-N{(i+1):06d}',
                'date': '2025-01-01',
                'hour': i % 24,
                'avg_speed_kmh': max(0, speed),
                'avg_duration_sec': max(0, duration),
                'n_valid': np.random.randint(1, 100)
            })
        
        return pd.DataFrame(data)


@pytest.fixture
def test_data_generator():
    """Provide test data generator instance."""
    return TestDataGenerator()


# Mock external dependencies
@pytest.fixture
def mock_folium_map():
    """Mock Folium map for testing without actual map rendering."""
    class MockMap:
        def __init__(self, location=None, zoom_start=10, tiles='OpenStreetMap'):
            self.location = location
            self.zoom_start = zoom_start
            self.tiles = tiles
            self.layers = []
        
        def add_child(self, child):
            self.layers.append(child)
        
        def get_root(self):
            return self
        
        @property
        def html(self):
            return self
        
        def add_child(self, element):
            pass
    
    return MockMap


# Performance testing utilities
@pytest.fixture
def performance_timer():
    """Utility for timing test operations."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
            return self.elapsed()
        
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )