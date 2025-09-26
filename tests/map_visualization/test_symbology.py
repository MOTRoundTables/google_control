"""
Tests for symbology and styling system.

This module tests the ColorSchemeManager, ClassificationEngine, and StyleCalculator
components of the map visualization symbology system.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

# Import the symbology classes
from symbology import (
    ColorSchemeManager, 
    ClassificationEngine, 
    StyleCalculator, 
    SymbologyEngine
)


class TestColorSchemeManager:
    """Test cases for ColorSchemeManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.color_manager = ColorSchemeManager()
    
    def test_initialization(self):
        """Test ColorSchemeManager initialization."""
        assert self.color_manager.duration_palette == 'RdYlGn_r'
        assert self.color_manager.speed_palette == 'RdYlGn'
        assert 'duration' in self.color_manager.available_palettes
        assert 'speed' in self.color_manager.available_palettes
    
    def test_get_color_palette_duration(self):
        """Test getting duration color palette."""
        colors = self.color_manager.get_color_palette('duration', n_colors=5)
        
        assert len(colors) == 5
        assert all(color.startswith('#') for color in colors)
        assert len(colors[0]) == 7  # Hex color format
    
    def test_get_color_palette_speed(self):
        """Test getting speed color palette."""
        colors = self.color_manager.get_color_palette('speed', n_colors=3)
        
        assert len(colors) == 3
        assert all(color.startswith('#') for color in colors)
    
    def test_get_color_palette_unknown_type(self):
        """Test getting palette for unknown metric type."""
        colors = self.color_manager.get_color_palette('unknown', n_colors=4)
        
        assert len(colors) == 4  # Should fallback to viridis
        assert all(color.startswith('#') for color in colors)
    
    def test_apply_color_scheme_basic(self):
        """Test basic color scheme application."""
        values = np.array([10, 20, 30, 40, 50])
        colors, class_breaks = self.color_manager.apply_color_scheme(
            values, 'duration', n_classes=3
        )
        
        assert len(colors) == len(values)
        assert len(class_breaks) == 4  # n_classes + 1
        assert all(color.startswith('#') for color in colors)
        assert class_breaks[0] <= class_breaks[-1]
    
    def test_apply_color_scheme_with_outlier_caps(self):
        """Test color scheme with outlier capping."""
        values = np.array([1, 10, 20, 30, 40, 50, 100])  # 100 is outlier
        colors, class_breaks = self.color_manager.apply_color_scheme(
            values, 'speed', outlier_caps=(10, 90), n_classes=3
        )
        
        assert len(colors) == len(values)
        assert len(class_breaks) == 4
        
        # Check that outliers are capped
        p10 = np.percentile(values, 10)
        p90 = np.percentile(values, 90)
        assert class_breaks[0] >= p10
        assert class_breaks[-1] <= p90
    
    def test_apply_color_scheme_empty_values(self):
        """Test color scheme with empty values."""
        values = np.array([])
        colors, class_breaks = self.color_manager.apply_color_scheme(
            values, 'duration'
        )
        
        assert colors == []
        assert class_breaks == []
    
    def test_apply_color_scheme_single_value(self):
        """Test color scheme with single value."""
        values = np.array([42])
        colors, class_breaks = self.color_manager.apply_color_scheme(
            values, 'duration', n_classes=3
        )
        
        assert len(colors) == 1
        assert len(class_breaks) == 4
        assert colors[0].startswith('#')


class TestClassificationEngine:
    """Test cases for ClassificationEngine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = ClassificationEngine()
        self.test_values = np.array([1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50])
    
    def test_initialization(self):
        """Test ClassificationEngine initialization."""
        expected_methods = ['quantiles', 'equal_interval', 'standard_deviation', 'manual']
        assert self.classifier.available_methods == expected_methods
    
    def test_quantile_classification(self):
        """Test quantile classification method."""
        class_indices, class_breaks = self.classifier.classify_data(
            self.test_values, method='quantiles', n_classes=5
        )
        
        assert len(class_indices) == len(self.test_values)
        assert len(class_breaks) == 6  # n_classes + 1
        assert class_breaks[0] <= class_breaks[-1]
        assert all(0 <= idx < 5 for idx in class_indices)
    
    def test_equal_interval_classification(self):
        """Test equal interval classification method."""
        class_indices, class_breaks = self.classifier.classify_data(
            self.test_values, method='equal_interval', n_classes=4
        )
        
        assert len(class_indices) == len(self.test_values)
        assert len(class_breaks) == 5
        
        # Check that intervals are approximately equal
        intervals = np.diff(class_breaks)
        assert np.allclose(intervals, intervals[0], rtol=1e-10)
    
    def test_standard_deviation_classification(self):
        """Test standard deviation classification method."""
        class_indices, class_breaks = self.classifier.classify_data(
            self.test_values, method='standard_deviation', n_classes=5
        )
        
        assert len(class_indices) == len(self.test_values)
        assert len(class_breaks) >= 5  # May have more breaks for std dev method
        
        # Check that breaks are centered around mean
        mean_val = self.test_values.mean()
        assert any(abs(class_break - mean_val) < 1 for class_break in class_breaks)
    
    def test_manual_classification(self):
        """Test manual classification method."""
        manual_breaks = [0, 10, 25, 40, 60]
        class_indices, class_breaks = self.classifier.classify_data(
            self.test_values, method='manual', manual_breaks=manual_breaks
        )
        
        assert len(class_indices) == len(self.test_values)
        assert class_breaks == sorted(manual_breaks)
        assert all(0 <= idx < len(manual_breaks) - 1 for idx in class_indices)
    
    def test_manual_classification_no_breaks(self):
        """Test manual classification without providing breaks."""
        with pytest.raises(ValueError, match="Manual breaks required"):
            self.classifier.classify_data(
                self.test_values, method='manual'
            )
    
    def test_invalid_method(self):
        """Test classification with invalid method."""
        with pytest.raises(ValueError, match="Method must be one of"):
            self.classifier.classify_data(
                self.test_values, method='invalid_method'
            )
    
    def test_empty_values(self):
        """Test classification with empty values."""
        empty_values = np.array([])
        class_indices, class_breaks = self.classifier.classify_data(
            empty_values, method='quantiles'
        )
        
        assert len(class_indices) == 0
        assert class_breaks == []
    
    def test_single_value(self):
        """Test classification with single value."""
        single_value = np.array([42])
        class_indices, class_breaks = self.classifier.classify_data(
            single_value, method='quantiles', n_classes=3
        )
        
        assert len(class_indices) == 1
        assert class_indices[0] == 0  # Should be in first class
        assert len(class_breaks) == 4


class TestStyleCalculator:
    """Test cases for StyleCalculator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.style_calc = StyleCalculator()
        self.test_values = np.array([1, 5, 10, 20, 50])
    
    def test_initialization(self):
        """Test StyleCalculator initialization."""
        assert self.style_calc.default_width_range == (1, 8)
        assert self.style_calc.default_opacity_range == (0.3, 1.0)
    
    def test_calculate_line_widths_linear(self):
        """Test linear line width calculation."""
        widths = self.style_calc.calculate_line_widths(
            self.test_values, mapping_type='linear'
        )
        
        assert len(widths) == len(self.test_values)
        assert all(1 <= w <= 8 for w in widths)  # Within default range
        assert widths[0] < widths[-1]  # Increasing with values
    
    def test_calculate_line_widths_log(self):
        """Test logarithmic line width calculation."""
        widths = self.style_calc.calculate_line_widths(
            self.test_values, mapping_type='log'
        )
        
        assert len(widths) == len(self.test_values)
        assert all(1 <= w <= 8 for w in widths)
        assert widths[0] < widths[-1]
    
    def test_calculate_line_widths_sqrt(self):
        """Test square root line width calculation."""
        widths = self.style_calc.calculate_line_widths(
            self.test_values, mapping_type='sqrt'
        )
        
        assert len(widths) == len(self.test_values)
        assert all(1 <= w <= 8 for w in widths)
        assert widths[0] < widths[-1]
    
    def test_calculate_line_widths_custom_range(self):
        """Test line width calculation with custom range."""
        custom_range = (0.5, 12)
        widths = self.style_calc.calculate_line_widths(
            self.test_values, width_range=custom_range
        )
        
        assert len(widths) == len(self.test_values)
        assert all(0.5 <= w <= 12 for w in widths)
    
    def test_calculate_line_widths_empty(self):
        """Test line width calculation with empty values."""
        widths = self.style_calc.calculate_line_widths(np.array([]))
        assert widths == []
    
    def test_calculate_opacity_sample_size(self):
        """Test opacity calculation based on sample size."""
        opacities = self.style_calc.calculate_opacity(
            self.test_values, confidence_type='sample_size'
        )
        
        assert len(opacities) == len(self.test_values)
        assert all(0.3 <= o <= 1.0 for o in opacities)  # Within default range
        assert opacities[0] < opacities[-1]  # Increasing with confidence
    
    def test_calculate_opacity_valid_hours(self):
        """Test opacity calculation based on valid hours share."""
        valid_hours_share = np.array([0.1, 0.3, 0.5, 0.8, 1.0])
        opacities = self.style_calc.calculate_opacity(
            valid_hours_share, confidence_type='valid_hours_share'
        )
        
        assert len(opacities) == len(valid_hours_share)
        assert all(0.3 <= o <= 1.0 for o in opacities)
        assert opacities[0] < opacities[-1]
    
    def test_calculate_opacity_custom_range(self):
        """Test opacity calculation with custom range."""
        custom_range = (0.1, 0.9)
        opacities = self.style_calc.calculate_opacity(
            self.test_values, opacity_range=custom_range
        )
        
        assert len(opacities) == len(self.test_values)
        assert all(0.1 <= o <= 0.9 for o in opacities)
    
    def test_calculate_opacity_empty(self):
        """Test opacity calculation with empty values."""
        opacities = self.style_calc.calculate_opacity(np.array([]))
        assert opacities == []
    
    def test_calculate_arrow_styles_disabled(self):
        """Test arrow styling when disabled."""
        test_data = pd.DataFrame({
            'link_id': ['s_1-2', 's_2-3'],
            'From': [1, 2],
            'To': [2, 3]
        })
        
        arrow_config = self.style_calc.calculate_arrow_styles(
            test_data, show_arrows=False
        )
        
        assert arrow_config['show_arrows'] is False
        assert arrow_config['arrow_position'] == 'end'
        assert arrow_config['arrow_size'] == 'small'
        assert arrow_config['arrow_color'] == 'inherit'
    
    def test_calculate_arrow_styles_enabled(self):
        """Test arrow styling when enabled."""
        test_data = pd.DataFrame({
            'link_id': ['s_1-2', 's_2-3'],
            'From': [1, 2],
            'To': [2, 3]
        })
        
        arrow_config = self.style_calc.calculate_arrow_styles(
            test_data, show_arrows=True
        )
        
        assert arrow_config['show_arrows'] is True
        assert arrow_config['arrow_position'] == 'end'  # At 'To' end


class TestSymbologyEngine:
    """Test cases for SymbologyEngine integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.symbology_engine = SymbologyEngine()
        self.test_data = pd.DataFrame({
            'link_id': ['s_1-2', 's_2-3', 's_3-4', 's_4-5'],
            'avg_duration_sec': [120, 180, 240, 300],
            'avg_speed_kmh': [45, 35, 25, 15],
            'n_valid': [10, 20, 30, 40],
            'From': [1, 2, 3, 4],
            'To': [2, 3, 4, 5]
        })
    
    def test_initialization(self):
        """Test SymbologyEngine initialization."""
        assert isinstance(self.symbology_engine.color_manager, ColorSchemeManager)
        assert isinstance(self.symbology_engine.classifier, ClassificationEngine)
        assert isinstance(self.symbology_engine.style_calculator, StyleCalculator)
    
    def test_create_symbology_duration(self):
        """Test creating symbology for duration metric."""
        config = {
            'metric_type': 'duration',
            'classification': 'quantiles',
            'n_classes': 3,
            'outlier_caps': (5, 95),
            'width_column': 'n_valid',
            'opacity_column': 'n_valid',
            'legend_title': 'Duration (minutes)'
        }
        
        symbology = self.symbology_engine.create_symbology(
            self.test_data, 'avg_duration_sec', config
        )
        
        # Check all required components are present
        assert 'colors' in symbology
        assert 'line_widths' in symbology
        assert 'opacities' in symbology
        assert 'class_breaks' in symbology
        assert 'class_indices' in symbology
        assert 'arrow_config' in symbology
        assert 'legend_config' in symbology
        
        # Check lengths match data
        assert len(symbology['colors']) == len(self.test_data)
        assert len(symbology['line_widths']) == len(self.test_data)
        assert len(symbology['opacities']) == len(self.test_data)
        assert len(symbology['class_indices']) == len(self.test_data)
        
        # Check legend configuration
        legend = symbology['legend_config']
        assert legend['title'] == 'Duration (minutes)'
        assert len(legend['class_breaks']) == 4  # n_classes + 1
        assert len(legend['colors']) == 3  # n_classes
        assert legend['outlier_caps'] == (5, 95)
    
    def test_create_symbology_speed(self):
        """Test creating symbology for speed metric."""
        config = {
            'metric_type': 'speed',
            'classification': 'equal_interval',
            'n_classes': 4,
            'show_arrows': True
        }
        
        symbology = self.symbology_engine.create_symbology(
            self.test_data, 'avg_speed_kmh', config
        )
        
        assert len(symbology['colors']) == len(self.test_data)
        assert symbology['arrow_config']['show_arrows'] is True
        assert len(symbology['legend_config']['colors']) == 4
    
    def test_create_symbology_missing_column(self):
        """Test creating symbology with missing metric column."""
        config = {'metric_type': 'duration'}
        
        with pytest.raises(ValueError, match="Metric column missing_column not found"):
            self.symbology_engine.create_symbology(
                self.test_data, 'missing_column', config
            )
    
    def test_create_symbology_default_values(self):
        """Test creating symbology with default width/opacity values."""
        # Remove n_valid column to test defaults
        test_data_no_n = self.test_data.drop(columns=['n_valid'])
        
        config = {
            'metric_type': 'duration',
            'width_column': 'n_valid',  # Missing column
            'opacity_column': 'n_valid'  # Missing column
        }
        
        symbology = self.symbology_engine.create_symbology(
            test_data_no_n, 'avg_duration_sec', config
        )
        
        # Should use default values
        assert all(w == 3 for w in symbology['line_widths'])  # Default width
        assert all(o == 0.8 for o in symbology['opacities'])  # Default opacity
    
    def test_create_symbology_manual_classification(self):
        """Test creating symbology with manual classification."""
        config = {
            'metric_type': 'speed',
            'classification': 'manual',
            'manual_breaks': [0, 20, 40, 60, 80],
            'n_classes': 4  # Should be ignored for manual
        }
        
        symbology = self.symbology_engine.create_symbology(
            self.test_data, 'avg_speed_kmh', config
        )
        
        assert symbology['class_breaks'] == [0, 20, 40, 60, 80]
        assert len(symbology['colors']) == len(self.test_data)


# Integration tests
class TestSymbologyIntegration:
    """Integration tests for symbology system."""
    
    def test_end_to_end_duration_symbology(self):
        """Test complete duration symbology workflow."""
        # Create realistic traffic data
        data = pd.DataFrame({
            'link_id': [f's_{i}-{i+1}' for i in range(1, 11)],
            'avg_duration_sec': [60, 90, 120, 150, 180, 210, 240, 270, 300, 330],
            'avg_speed_kmh': [50, 45, 40, 35, 30, 25, 20, 15, 10, 5],
            'n_valid': [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
            'From': list(range(1, 11)),
            'To': list(range(2, 12))
        })
        
        engine = SymbologyEngine()
        config = {
            'metric_type': 'duration',
            'classification': 'quantiles',
            'n_classes': 5,
            'outlier_caps': (10, 90),
            'width_column': 'n_valid',
            'opacity_column': 'n_valid',
            'width_range': (1, 6),
            'opacity_range': (0.4, 1.0),
            'show_arrows': True,
            'legend_title': 'Travel Time (minutes)'
        }
        
        symbology = engine.create_symbology(data, 'avg_duration_sec', config)
        
        # Verify complete symbology
        assert len(symbology['colors']) == 10
        assert len(symbology['line_widths']) == 10
        assert len(symbology['opacities']) == 10
        assert len(symbology['class_breaks']) == 6  # n_classes + 1
        
        # Check value ranges
        assert all(1 <= w <= 6 for w in symbology['line_widths'])
        assert all(0.4 <= o <= 1.0 for o in symbology['opacities'])
        assert all(color.startswith('#') for color in symbology['colors'])
        
        # Check arrow configuration
        assert symbology['arrow_config']['show_arrows'] is True
        assert symbology['arrow_config']['arrow_position'] == 'end'
        
        # Check legend
        legend = symbology['legend_config']
        assert legend['title'] == 'Travel Time (minutes)'
        assert len(legend['colors']) == 5
        assert legend['outlier_caps'] == (10, 90)
    
    def test_end_to_end_speed_symbology(self):
        """Test complete speed symbology workflow."""
        data = pd.DataFrame({
            'link_id': [f's_{i}-{i+1}' for i in range(1, 6)],
            'avg_speed_kmh': [10, 25, 40, 55, 70],
            'n_valid': [8, 16, 24, 32, 40],
            'From': list(range(1, 6)),
            'To': list(range(2, 7))
        })
        
        engine = SymbologyEngine()
        config = {
            'metric_type': 'speed',
            'classification': 'equal_interval',
            'n_classes': 3,
            'width_column': 'n_valid',
            'opacity_column': 'n_valid',
            'show_arrows': False,
            'legend_title': 'Speed (km/h)'
        }
        
        symbology = engine.create_symbology(data, 'avg_speed_kmh', config)
        
        # Verify symbology components
        assert len(symbology['colors']) == 5
        assert len(symbology['line_widths']) == 5
        assert len(symbology['opacities']) == 5
        assert len(symbology['class_breaks']) == 4
        
        # Check that speed uses correct palette (red to green)
        assert symbology['arrow_config']['show_arrows'] is False
        
        # Verify equal interval classification
        breaks = symbology['class_breaks']
        intervals = [breaks[i+1] - breaks[i] for i in range(len(breaks)-1)]
        assert all(abs(interval - intervals[0]) < 1e-10 for interval in intervals)


if __name__ == '__main__':
    pytest.main([__file__])