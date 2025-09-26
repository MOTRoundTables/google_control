"""
Tests for KPI calculations and performance optimizations.

This module tests the KPI calculation engine and performance optimization
components to ensure accurate metrics and responsive rendering.
"""

import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Point
import numpy as np
from datetime import date, datetime, timedelta
import tempfile
import os
import shutil

# Import modules to test
from kpi_engine import KPICalculationEngine
from performance_optimizer import (
    PerformanceOptimizer, GeometrySimplifier, ViewportRenderer, 
    CachingSystem, PerformanceMonitor
)


class TestKPICalculationEngine:
    """Test cases for KPI calculation engine."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample GeoDataFrame for testing."""
        # Create sample geometries
        geometries = [
            LineString([(0, 0), (1, 0)]),
            LineString([(1, 0), (2, 0)]),
            LineString([(2, 0), (3, 0)]),
            LineString([(0, 1), (1, 1)]),
            LineString([(1, 1), (2, 1)])
        ]
        
        data = {
            'Id': ['L001', 'L002', 'L003', 'L004', 'L005'],
            'From': ['N001', 'N002', 'N003', 'N001', 'N002'],
            'To': ['N002', 'N003', 'N004', 'N002', 'N003'],
            'avg_speed_kmh': [45.5, 32.1, 67.8, 28.9, 55.2],
            'avg_duration_sec': [120, 180, 90, 240, 110],
            'length_m': [1000, 1500, 800, 1200, 900],
            'n_valid': [25, 18, 32, 12, 28],
            'geometry': geometries
        }
        
        return gpd.GeoDataFrame(data, crs='EPSG:4326')
    
    @pytest.fixture
    def sample_results(self):
        """Create sample results DataFrame."""
        dates = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
        hours = [7, 8, 9, 17, 18, 19]
        
        data = []
        for d in dates:
            for h in hours:
                for link_id in ['s_N001-N002', 's_N002-N003', 's_N003-N004']:
                    data.append({
                        'link_id': link_id,
                        'date': d,
                        'hour': h,
                        'avg_speed_kmh': np.random.normal(45, 10),
                        'avg_duration_sec': np.random.normal(150, 30),
                        'n_valid': np.random.randint(5, 30)
                    })
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def kpi_engine(self):
        """Create KPI calculation engine instance."""
        return KPICalculationEngine()
    
    def test_calculate_comprehensive_kpis(self, kpi_engine, sample_data):
        """Test comprehensive KPI calculation."""
        total_links = 10
        date_context = {'n_days': 3, 'date_range_str': '2024-01-01 to 2024-01-03'}
        
        kpis = kpi_engine.calculate_comprehensive_kpis(
            sample_data, total_links, date_context
        )
        
        # Check that all expected KPIs are present
        expected_kpis = [
            'coverage_percent', 'mean_speed', 'mean_duration', 'n_links_rendered',
            'total_observations', 'network_length_km', 'data_quality_score'
        ]
        
        for kpi in expected_kpis:
            assert kpi in kpis, f"Missing KPI: {kpi}"
        
        # Check specific calculations
        assert kpis['coverage_percent'] == 50.0  # 5 links out of 10
        assert kpis['n_links_rendered'] == 5
        assert abs(kpis['mean_speed'] - sample_data['avg_speed_kmh'].mean()) < 0.01
        assert abs(kpis['mean_duration'] - sample_data['avg_duration_sec'].mean() / 60) < 0.01
        assert kpis['total_observations'] == sample_data['n_valid'].sum()
        assert abs(kpis['network_length_km'] - sample_data['length_m'].sum() / 1000) < 0.01
    
    def test_empty_data_kpis(self, kpi_engine):
        """Test KPI calculation with empty data."""
        empty_data = gpd.GeoDataFrame()
        kpis = kpi_engine.calculate_comprehensive_kpis(empty_data, 10)
        
        # Should return zero values for all metrics
        assert kpis['coverage_percent'] == 0
        assert kpis['n_links_rendered'] == 0
        assert kpis['mean_speed'] == 0
        assert kpis['data_quality_score'] == 0
    
    def test_reactive_kpis(self, kpi_engine, sample_data):
        """Test reactive KPI updates with change tracking."""
        # First calculation
        kpis1 = kpi_engine.calculate_reactive_kpis(
            sample_data, None, 10
        )
        
        # Modify data for second calculation
        modified_data = sample_data.copy()
        modified_data['avg_speed_kmh'] = modified_data['avg_speed_kmh'] * 1.1  # 10% increase
        
        kpis2 = kpi_engine.calculate_reactive_kpis(
            modified_data, kpis1, 10
        )
        
        # Check that changes are tracked
        assert 'changes' in kpis2
        assert 'mean_speed_change' in kpis2['changes']
        assert kpis2['changes']['mean_speed_change'] > 0  # Should show increase
    
    def test_data_quality_assessment(self, kpi_engine, sample_data):
        """Test data quality scoring."""
        # Test with good quality data
        kpis = kpi_engine.calculate_comprehensive_kpis(sample_data, 10)
        assert kpis['data_quality_score'] > 50
        assert kpis['quality_assessment'] in ['good', 'excellent', 'moderate']
        
        # Test with poor quality data
        poor_data = sample_data.copy()
        poor_data['avg_speed_kmh'] = [-10, 300, 0, -5, 500]  # Invalid speeds
        poor_data['n_valid'] = [1, 2, 1, 1, 2]  # Very low observation counts
        
        poor_kpis = kpi_engine.calculate_comprehensive_kpis(poor_data, 10)
        assert poor_kpis['data_quality_score'] < kpis['data_quality_score']
    
    def test_kpi_formatting(self, kpi_engine, sample_data):
        """Test KPI formatting for display."""
        kpis = kpi_engine.calculate_comprehensive_kpis(sample_data, 10)
        
        # Test different metric formatting
        value, unit, change = kpi_engine.format_kpi_for_display(kpis, 'coverage_percent')
        assert unit == "%"
        assert float(value) == 50.0
        
        value, unit, change = kpi_engine.format_kpi_for_display(kpis, 'mean_speed')
        assert unit == "km/h"
        
        value, unit, change = kpi_engine.format_kpi_for_display(kpis, 'n_links_rendered')
        assert unit == ""
        assert int(value.replace(',', '')) == 5
    
    def test_kpi_summary_text(self, kpi_engine, sample_data):
        """Test KPI summary text generation."""
        kpis = kpi_engine.calculate_comprehensive_kpis(sample_data, 10)
        summary = kpi_engine.get_kpi_summary_text(kpis)
        
        assert "5 links" in summary
        assert "50.0% coverage" in summary
        assert "Data quality:" in summary


class TestGeometrySimplifier:
    """Test cases for geometry simplification."""
    
    @pytest.fixture
    def complex_geometry_data(self):
        """Create GeoDataFrame with complex geometries."""
        # Create complex line with many points
        complex_line = LineString([
            (0, 0), (0.1, 0.05), (0.2, 0.02), (0.3, 0.08), (0.4, 0.03),
            (0.5, 0.07), (0.6, 0.01), (0.7, 0.09), (0.8, 0.04), (1, 0)
        ])
        
        simple_line = LineString([(0, 1), (1, 1)])
        
        data = {
            'Id': ['L001', 'L002'],
            'length_m': [1000, 500],
            'geometry': [complex_line, simple_line]
        }
        
        return gpd.GeoDataFrame(data, crs='EPSG:4326')
    
    @pytest.fixture
    def simplifier(self):
        """Create geometry simplifier instance."""
        return GeometrySimplifier()
    
    def test_simplify_for_zoom_level(self, simplifier, complex_geometry_data):
        """Test geometry simplification at different zoom levels."""
        # Test high zoom (minimal simplification)
        high_zoom_result = simplifier.simplify_for_zoom_level(complex_geometry_data, 15)
        assert len(high_zoom_result) == 2
        
        # Test low zoom (high simplification)
        low_zoom_result = simplifier.simplify_for_zoom_level(complex_geometry_data, 1)
        
        # Should have fewer coordinate points after simplification
        original_coords = len(complex_geometry_data.iloc[0].geometry.coords)
        simplified_coords = len(low_zoom_result.iloc[0].geometry.coords)
        assert simplified_coords <= original_coords
    
    def test_feature_filtering_by_size(self, simplifier):
        """Test filtering of small features at low zoom levels."""
        # Create data with different sized features
        geometries = [
            LineString([(0, 0), (1, 0)]),  # 1000m
            LineString([(0, 1), (0.1, 1)]),  # 100m
            LineString([(0, 2), (0.01, 2)])  # 10m
        ]
        
        data = gpd.GeoDataFrame({
            'Id': ['L001', 'L002', 'L003'],
            'length_m': [1000, 100, 10],
            'geometry': geometries
        }, crs='EPSG:4326')
        
        # At zoom level 1, should filter out small features
        result = simplifier.simplify_for_zoom_level(data, 1)
        assert len(result) < len(data)  # Some features should be filtered out
        
        # At high zoom, should keep all features
        result_high = simplifier.simplify_for_zoom_level(data, 15)
        assert len(result_high) == len(data)
    
    def test_calculate_optimal_zoom_level(self, simplifier):
        """Test optimal zoom level calculation."""
        # Test different viewport scenarios
        large_bounds = (0, 0, 10000, 10000)  # Large area
        small_bounds = (0, 0, 100, 100)      # Small area
        viewport = (800, 600)                # Standard viewport
        
        large_zoom = simplifier.calculate_optimal_zoom_level(large_bounds, viewport)
        small_zoom = simplifier.calculate_optimal_zoom_level(small_bounds, viewport)
        
        # Smaller area should result in higher zoom level
        assert small_zoom > large_zoom
        assert 1 <= large_zoom <= 15
        assert 1 <= small_zoom <= 15


class TestViewportRenderer:
    """Test cases for viewport rendering."""
    
    @pytest.fixture
    def viewport_data(self):
        """Create data for viewport testing."""
        # Create features inside and outside viewport
        geometries = [
            LineString([(0, 0), (1, 0)]),    # Inside
            LineString([(5, 5), (6, 5)]),    # Inside
            LineString([(20, 20), (21, 20)]) # Outside
        ]
        
        return gpd.GeoDataFrame({
            'Id': ['L001', 'L002', 'L003'],
            'geometry': geometries
        }, crs='EPSG:4326')
    
    @pytest.fixture
    def renderer(self):
        """Create viewport renderer instance."""
        return ViewportRenderer()
    
    def test_filter_to_viewport(self, renderer, viewport_data):
        """Test viewport filtering."""
        viewport_bounds = (0, 0, 10, 10)  # Should include first two features
        
        result = renderer.filter_to_viewport(viewport_data, viewport_bounds)
        
        # Should filter out the feature at (20, 20)
        assert len(result) < len(viewport_data)
        assert len(result) >= 2  # Should include features in viewport
    
    def test_progressive_batches(self, renderer, viewport_data):
        """Test progressive batch creation."""
        renderer.progressive_batch_size = 2
        
        batches = renderer.create_progressive_batches(viewport_data)
        
        assert len(batches) >= 1
        total_features = sum(len(batch) for batch in batches)
        assert total_features == len(viewport_data)
    
    def test_rendering_time_estimation(self, renderer):
        """Test rendering time estimation."""
        small_time = renderer.estimate_rendering_time(100)
        large_time = renderer.estimate_rendering_time(10000)
        
        assert large_time > small_time
        assert small_time > 0
        assert large_time > 0


class TestCachingSystem:
    """Test cases for caching system."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def caching_system(self, temp_cache_dir):
        """Create caching system instance."""
        return CachingSystem(temp_cache_dir)
    
    def test_cache_key_generation(self, caching_system):
        """Test cache key generation."""
        key1 = caching_system.generate_cache_key(
            'duration', (7, 8, 9), ('2024-01-01', '2024-01-03'), {'length': {'operator': 'above', 'value': 1000}}
        )
        
        key2 = caching_system.generate_cache_key(
            'speed', (7, 8, 9), ('2024-01-01', '2024-01-03'), {'length': {'operator': 'above', 'value': 1000}}
        )
        
        # Different metrics should produce different keys
        assert key1 != key2
        assert len(key1) == 32  # MD5 hash length
        assert len(key2) == 32
    
    def test_cache_operations(self, caching_system):
        """Test caching and retrieval operations."""
        test_data = {'test': 'data', 'numbers': [1, 2, 3]}
        cache_key = 'test_key'
        
        # Test caching
        success = caching_system.cache_data(cache_key, test_data)
        assert success
        
        # Test retrieval
        retrieved_data = caching_system.get_cached_data(cache_key)
        assert retrieved_data == test_data
        
        # Test non-existent key
        missing_data = caching_system.get_cached_data('non_existent_key')
        assert missing_data is None
    
    def test_cache_expiration(self, caching_system):
        """Test cache expiration functionality."""
        # Set very short expiration for testing
        caching_system.max_cache_age_hours = 0.001  # ~3.6 seconds
        
        test_data = {'test': 'expiration'}
        cache_key = 'expiration_test'
        
        # Cache data
        caching_system.cache_data(cache_key, test_data)
        
        # Should be available immediately
        assert caching_system.get_cached_data(cache_key) == test_data
        
        # Wait for expiration (in real implementation, would need to wait)
        # For testing, we'll manually modify the file timestamp
        import time
        cache_file = os.path.join(caching_system.cache_dir, f"{cache_key}.pkl")
        if os.path.exists(cache_file):
            # Set file time to past
            old_time = time.time() - 3700  # 1 hour ago
            os.utime(cache_file, (old_time, old_time))
            
            # Should now return None due to expiration
            assert caching_system.get_cached_data(cache_key) is None


class TestPerformanceMonitor:
    """Test cases for performance monitoring."""
    
    @pytest.fixture
    def monitor(self):
        """Create performance monitor instance."""
        return PerformanceMonitor()
    
    def test_performance_logging(self, monitor):
        """Test performance logging functionality."""
        # Log a successful operation
        monitor.log_performance('test_operation', 0.5, success=True)
        
        # Log a failed operation
        monitor.log_performance('test_operation', 1.0, success=False, error='Test error')
        
        assert len(monitor.performance_log) == 2
        assert monitor.performance_log[0]['operation'] == 'test_operation'
        assert monitor.performance_log[0]['success'] is True
        assert monitor.performance_log[1]['success'] is False
    
    def test_performance_decorator(self, monitor):
        """Test performance timing decorator."""
        @monitor.time_operation('test_function')
        def test_function(x, y):
            time.sleep(0.01)  # Small delay for testing
            return x + y
        
        result = test_function(1, 2)
        assert result == 3
        assert len(monitor.performance_log) == 1
        assert monitor.performance_log[0]['operation'] == 'test_function'
        assert monitor.performance_log[0]['duration'] > 0.01
    
    def test_performance_summary(self, monitor):
        """Test performance summary generation."""
        # Log multiple operations
        for i in range(5):
            monitor.log_performance('test_op', 0.1 + i * 0.1, success=True)
        
        summary = monitor.get_performance_summary()
        
        assert 'test_op' in summary
        assert summary['test_op']['count'] == 5
        assert summary['test_op']['success_count'] == 5
        assert summary['test_op']['mean_duration'] > 0


class TestPerformanceOptimizer:
    """Test cases for performance optimizer integration."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def optimizer(self, temp_cache_dir):
        """Create performance optimizer instance."""
        return PerformanceOptimizer(temp_cache_dir)
    
    @pytest.fixture
    def test_data(self):
        """Create test data for optimization."""
        geometries = [LineString([(i, 0), (i+1, 0)]) for i in range(10)]
        
        return gpd.GeoDataFrame({
            'Id': [f'L{i:03d}' for i in range(10)],
            'length_m': [1000 + i * 100 for i in range(10)],
            'geometry': geometries
        }, crs='EPSG:4326')
    
    def test_optimize_data_for_rendering(self, optimizer, test_data):
        """Test integrated data optimization."""
        viewport_bounds = (0, -1, 5, 1)  # Should include first 5 features
        zoom_level = 10
        
        optimized = optimizer.optimize_data_for_rendering(
            test_data, zoom_level, viewport_bounds
        )
        
        # Should have fewer features due to viewport filtering
        assert len(optimized) <= len(test_data)
        assert len(optimized) > 0
    
    def test_rendering_strategy(self, optimizer):
        """Test rendering strategy creation."""
        # Test with small dataset
        small_strategy = optimizer.create_rendering_strategy(500, (800, 600))
        assert not small_strategy['use_progressive_rendering']
        
        # Test with large dataset
        large_strategy = optimizer.create_rendering_strategy(15000, (800, 600))
        assert large_strategy['use_progressive_rendering']
        assert large_strategy['use_viewport_filtering']
        assert large_strategy['use_geometry_simplification']
    
    def test_performance_report(self, optimizer):
        """Test performance report generation."""
        report = optimizer.get_performance_report()
        
        assert 'performance_summary' in report
        assert 'cache_statistics' in report
        assert 'optimization_settings' in report
        
        # Check cache statistics
        cache_stats = report['cache_statistics']
        assert 'cache_size_mb' in cache_stats
        assert 'max_cache_size_mb' in cache_stats


class TestIntegration:
    """Integration tests for KPI and performance systems."""
    
    @pytest.fixture
    def integrated_system(self):
        """Create integrated system with KPI engine and performance optimizer."""
        temp_dir = tempfile.mkdtemp()
        
        system = {
            'kpi_engine': KPICalculationEngine(),
            'optimizer': PerformanceOptimizer(temp_dir),
            'temp_dir': temp_dir
        }
        
        yield system
        
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def realistic_data(self):
        """Create realistic test data."""
        np.random.seed(42)  # For reproducible tests
        
        # Create network geometry
        n_links = 1000
        geometries = []
        for i in range(n_links):
            start_x = np.random.uniform(0, 100)
            start_y = np.random.uniform(0, 100)
            end_x = start_x + np.random.uniform(-5, 5)
            end_y = start_y + np.random.uniform(-5, 5)
            geometries.append(LineString([(start_x, start_y), (end_x, end_y)]))
        
        # Create realistic traffic data
        data = {
            'Id': [f'L{i:04d}' for i in range(n_links)],
            'From': [f'N{i:04d}' for i in range(n_links)],
            'To': [f'N{i+1:04d}' for i in range(n_links)],
            'avg_speed_kmh': np.random.normal(45, 15, n_links).clip(5, 120),
            'avg_duration_sec': np.random.normal(180, 60, n_links).clip(30, 600),
            'length_m': np.random.normal(1000, 300, n_links).clip(100, 5000),
            'n_valid': np.random.poisson(20, n_links).clip(1, 100),
            'geometry': geometries
        }
        
        return gpd.GeoDataFrame(data, crs='EPSG:4326')
    
    def test_end_to_end_optimization_and_kpis(self, integrated_system, realistic_data):
        """Test end-to-end optimization and KPI calculation."""
        kpi_engine = integrated_system['kpi_engine']
        optimizer = integrated_system['optimizer']
        
        # Test with large dataset
        total_network_links = 2000
        viewport_bounds = (0, 0, 50, 50)
        zoom_level = 8
        
        # Optimize data for rendering
        optimized_data = optimizer.optimize_data_for_rendering(
            realistic_data, zoom_level, viewport_bounds
        )
        
        # Calculate KPIs on optimized data
        date_context = {
            'n_days': 7,
            'date_range_str': '2024-01-01 to 2024-01-07'
        }
        
        kpis = kpi_engine.calculate_comprehensive_kpis(
            optimized_data, total_network_links, date_context, realistic_data
        )
        
        # Verify results
        assert kpis['n_links_rendered'] <= len(realistic_data)
        assert kpis['coverage_percent'] <= 100
        assert kpis['data_quality_score'] > 0
        assert kpis['mean_speed'] > 0
        assert kpis['mean_duration'] > 0
    
    def test_caching_with_kpis(self, integrated_system, realistic_data):
        """Test caching integration with KPI calculations."""
        optimizer = integrated_system['optimizer']
        
        # Create cache key
        cache_key = optimizer.caching_system.generate_cache_key(
            'duration', (7, 8, 9), ('2024-01-01', '2024-01-03'), {}
        )
        
        # First optimization (should cache result)
        optimized1 = optimizer.optimize_data_for_rendering(
            realistic_data, 10, cache_key=cache_key
        )
        
        # Second optimization (should use cache)
        optimized2 = optimizer.optimize_data_for_rendering(
            realistic_data, 10, cache_key=cache_key
        )
        
        # Results should be identical
        assert len(optimized1) == len(optimized2)
        pd.testing.assert_frame_equal(
            optimized1.drop(columns=['geometry']), 
            optimized2.drop(columns=['geometry'])
        )


if __name__ == "__main__":
    pytest.main([__file__])