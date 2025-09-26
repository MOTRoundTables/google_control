"""
Symbology and styling module for interactive map visualization.

This module handles color schemes, classification methods, and visual styling
for the traffic monitoring GUI's map visualization feature.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Any, Optional
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import logging

# Try to import sklearn, use fallback if not available
try:
    from sklearn.preprocessing import MinMaxScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    # Simple fallback scaler
    class MinMaxScaler:
        def __init__(self, feature_range=(0, 1)):
            self.feature_range = feature_range
            self.min_ = None
            self.scale_ = None
        
        def fit_transform(self, X):
            X = np.array(X).reshape(-1, 1) if X.ndim == 1 else np.array(X)
            self.min_ = X.min(axis=0)
            self.scale_ = (X.max(axis=0) - self.min_) / (self.feature_range[1] - self.feature_range[0])
            return ((X - self.min_) / self.scale_) * (self.feature_range[1] - self.feature_range[0]) + self.feature_range[0]

logger = logging.getLogger(__name__)


class ColorSchemeManager:
    """Manages color palettes for duration and speed visualization."""
    
    def __init__(self):
        # Duration palette: green (low) to red (high)
        self.duration_palette = 'RdYlGn_r'  # Reversed Red-Yellow-Green
        # Speed palette: red (low) to green (high) 
        self.speed_palette = 'RdYlGn'  # Red-Yellow-Green
        
        self.available_palettes = {
            'duration': self.duration_palette,
            'speed': self.speed_palette,
            'sequential': 'viridis',
            'diverging': 'RdBu_r'
        }
    
    def get_color_palette(self, metric_type: str, n_colors: int = 5) -> List[str]:
        """
        Get color palette for specific metric type.
        
        Args:
            metric_type: Type of metric ('duration', 'speed', etc.)
            n_colors: Number of colors in palette
            
        Returns:
            List of hex color codes
        """
        palette_name = self.available_palettes.get(metric_type, 'viridis')
        
        # Get colormap
        cmap = plt.get_cmap(palette_name)
        
        # Generate colors
        colors = [mcolors.rgb2hex(cmap(i / (n_colors - 1))) for i in range(n_colors)]
        
        logger.debug(f"Generated {n_colors} colors for {metric_type} using {palette_name}")
        return colors
    
    def apply_color_scheme(self, values: np.array, metric_type: str, 
                          outlier_caps: Optional[Tuple[float, float]] = None,
                          n_classes: int = 5) -> Tuple[List[str], List[float]]:
        """
        Apply color scheme to values with optional outlier capping.
        
        Args:
            values: Array of values to color
            metric_type: Type of metric for palette selection
            outlier_caps: Optional tuple of (lower_percentile, upper_percentile)
            n_classes: Number of color classes
            
        Returns:
            Tuple of (colors, class_breaks)
        """
        if len(values) == 0:
            return [], []
        
        # Apply outlier capping if specified
        if outlier_caps:
            lower_cap = np.percentile(values, outlier_caps[0])
            upper_cap = np.percentile(values, outlier_caps[1])
            capped_values = np.clip(values, lower_cap, upper_cap)
            logger.debug(f"Applied outlier caps: {lower_cap:.2f} to {upper_cap:.2f}")
        else:
            capped_values = values
        
        # Get color palette
        palette_colors = self.get_color_palette(metric_type, n_classes)
        
        # Create class breaks
        class_breaks = np.linspace(capped_values.min(), capped_values.max(), n_classes + 1)
        
        # Assign colors to values
        colors = []
        for value in capped_values:
            class_idx = np.digitize(value, class_breaks) - 1
            class_idx = max(0, min(class_idx, n_classes - 1))  # Clamp to valid range
            colors.append(palette_colors[class_idx])
        
        return colors, class_breaks.tolist()


class ClassificationEngine:
    """Implements various classification methods for data visualization."""
    
    def __init__(self):
        self.available_methods = ['quantiles', 'equal_interval', 'standard_deviation', 'manual']
    
    def classify_data(self, values: np.array, method: str = 'quantiles', 
                     n_classes: int = 5, manual_breaks: Optional[List[float]] = None) -> Tuple[np.array, List[float]]:
        """
        Classify data using specified method.
        
        Args:
            values: Array of values to classify
            method: Classification method
            n_classes: Number of classes (ignored for manual)
            manual_breaks: Manual break points for manual method
            
        Returns:
            Tuple of (class_indices, class_breaks)
        """
        if method not in self.available_methods:
            raise ValueError(f"Method must be one of {self.available_methods}")
        
        if len(values) == 0:
            return np.array([]), []
        
        if method == 'quantiles':
            return self._quantile_classification(values, n_classes)
        elif method == 'equal_interval':
            return self._equal_interval_classification(values, n_classes)
        elif method == 'standard_deviation':
            return self._standard_deviation_classification(values, n_classes)
        elif method == 'manual':
            if manual_breaks is None:
                raise ValueError("Manual breaks required for manual classification")
            return self._manual_classification(values, manual_breaks)
    
    def _quantile_classification(self, values: np.array, n_classes: int) -> Tuple[np.array, List[float]]:
        """Classify using quantiles (equal count)."""
        quantiles = np.linspace(0, 100, n_classes + 1)
        class_breaks = np.percentile(values, quantiles)
        class_indices = np.digitize(values, class_breaks) - 1
        class_indices = np.clip(class_indices, 0, n_classes - 1)
        
        logger.debug(f"Quantile classification: {len(np.unique(class_indices))} classes")
        return class_indices, class_breaks.tolist()
    
    def _equal_interval_classification(self, values: np.array, n_classes: int) -> Tuple[np.array, List[float]]:
        """Classify using equal intervals."""
        min_val, max_val = values.min(), values.max()
        class_breaks = np.linspace(min_val, max_val, n_classes + 1)
        class_indices = np.digitize(values, class_breaks) - 1
        class_indices = np.clip(class_indices, 0, n_classes - 1)
        
        logger.debug(f"Equal interval classification: {len(np.unique(class_indices))} classes")
        return class_indices, class_breaks.tolist()
    
    def _standard_deviation_classification(self, values: np.array, n_classes: int) -> Tuple[np.array, List[float]]:
        """Classify using standard deviation breaks."""
        mean_val = values.mean()
        std_val = values.std()
        
        # Create breaks around mean ± n*std
        half_classes = n_classes // 2
        class_breaks = []
        
        for i in range(-half_classes, half_classes + 1):
            class_breaks.append(mean_val + i * std_val)
        
        # Ensure breaks cover data range
        class_breaks[0] = min(class_breaks[0], values.min())
        class_breaks[-1] = max(class_breaks[-1], values.max())
        
        class_breaks = sorted(class_breaks)
        class_indices = np.digitize(values, class_breaks) - 1
        class_indices = np.clip(class_indices, 0, len(class_breaks) - 2)
        
        logger.debug(f"Standard deviation classification: {len(np.unique(class_indices))} classes")
        return class_indices, class_breaks
    
    def _manual_classification(self, values: np.array, manual_breaks: List[float]) -> Tuple[np.array, List[float]]:
        """Classify using manual break points."""
        class_breaks = sorted(manual_breaks)
        class_indices = np.digitize(values, class_breaks) - 1
        class_indices = np.clip(class_indices, 0, len(class_breaks) - 2)
        
        logger.debug(f"Manual classification: {len(np.unique(class_indices))} classes")
        return class_indices, class_breaks


class StyleCalculator:
    """Calculates visual properties like line width and opacity."""
    
    def __init__(self):
        self.default_width_range = (1, 8)
        self.default_opacity_range = (0.3, 1.0)
    
    def calculate_line_widths(self, values: np.array, width_range: Tuple[float, float] = None,
                            mapping_type: str = 'linear') -> List[float]:
        """
        Calculate line widths based on values.
        
        Args:
            values: Array of values (observation count or link length)
            width_range: Tuple of (min_width, max_width)
            mapping_type: Type of mapping ('linear', 'log', 'sqrt')
            
        Returns:
            List of line widths
        """
        if width_range is None:
            width_range = self.default_width_range
        
        if len(values) == 0:
            return []
        
        # Apply transformation based on mapping type
        if mapping_type == 'log':
            transformed_values = np.log1p(values)  # log(1 + x) to handle zeros
        elif mapping_type == 'sqrt':
            transformed_values = np.sqrt(values)
        else:  # linear
            transformed_values = values
        
        # Scale to width range
        scaler = MinMaxScaler(feature_range=width_range)
        scaled_widths = scaler.fit_transform(transformed_values.reshape(-1, 1)).flatten()
        
        logger.debug(f"Calculated line widths: {scaled_widths.min():.1f} to {scaled_widths.max():.1f}")
        return scaled_widths.tolist()
    
    def calculate_opacity(self, confidence_values: np.array, 
                         opacity_range: Tuple[float, float] = None,
                         confidence_type: str = 'sample_size') -> List[float]:
        """
        Calculate opacity based on confidence indicators.
        
        Args:
            confidence_values: Array of confidence values (N observations or valid hours share)
            opacity_range: Tuple of (min_opacity, max_opacity)
            confidence_type: Type of confidence measure
            
        Returns:
            List of opacity values
        """
        if opacity_range is None:
            opacity_range = self.default_opacity_range
        
        if len(confidence_values) == 0:
            return []
        
        # Transform confidence values if needed
        if confidence_type == 'sample_size':
            # Use log scale for sample size to avoid extreme differences
            transformed_values = np.log1p(confidence_values)
        else:  # valid_hours_share or other ratio
            transformed_values = confidence_values
        
        # Scale to opacity range
        scaler = MinMaxScaler(feature_range=opacity_range)
        scaled_opacity = scaler.fit_transform(transformed_values.reshape(-1, 1)).flatten()
        
        logger.debug(f"Calculated opacity: {scaled_opacity.min():.2f} to {scaled_opacity.max():.2f}")
        return scaled_opacity.tolist()
    
    def calculate_arrow_styles(self, data: pd.DataFrame, show_arrows: bool = False) -> Dict[str, Any]:
        """
        Calculate arrow styling for directed links.
        
        Args:
            data: DataFrame with link data
            show_arrows: Whether to show direction arrows
            
        Returns:
            Dictionary with arrow styling configuration
        """
        arrow_config = {
            'show_arrows': show_arrows,
            'arrow_position': 'end',  # At 'To' end
            'arrow_size': 'small',
            'arrow_color': 'inherit'  # Use same color as link
        }
        
        if show_arrows:
            logger.debug("Arrow styling enabled for directed links")
        
        return arrow_config


class SymbologyEngine:
    """Main interface for symbology operations."""
    
    def __init__(self):
        self.color_manager = ColorSchemeManager()
        self.classifier = ClassificationEngine()
        self.style_calculator = StyleCalculator()
    
    def create_symbology(self, data: pd.DataFrame, metric_column: str, 
                        config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create complete symbology for data visualization.
        
        Args:
            data: DataFrame with data to symbolize
            metric_column: Column name for primary metric
            config: Symbology configuration
            
        Returns:
            Dictionary with complete symbology specification
        """
        if metric_column not in data.columns:
            raise ValueError(f"Metric column {metric_column} not found in data")
        
        values = data[metric_column].values
        
        # Classification
        classification_method = config.get('classification', 'quantiles')
        n_classes = config.get('n_classes', 5)
        manual_breaks = config.get('manual_breaks')
        
        class_indices, class_breaks = self.classifier.classify_data(
            values, classification_method, n_classes, manual_breaks
        )
        
        # Color scheme
        metric_type = config.get('metric_type', 'duration')
        outlier_caps = config.get('outlier_caps', (2, 98))
        
        colors, color_breaks = self.color_manager.apply_color_scheme(
            values, metric_type, outlier_caps, n_classes
        )
        
        # Line widths
        width_column = config.get('width_column', 'n_valid')
        if width_column in data.columns:
            width_values = data[width_column].values
            line_widths = self.style_calculator.calculate_line_widths(
                width_values, config.get('width_range', (1, 8))
            )
        else:
            line_widths = [3] * len(data)  # Default width
        
        # Opacity
        opacity_column = config.get('opacity_column', 'n_valid')
        if opacity_column in data.columns:
            opacity_values = data[opacity_column].values
            opacities = self.style_calculator.calculate_opacity(
                opacity_values, config.get('opacity_range', (0.3, 1.0))
            )
        else:
            opacities = [0.8] * len(data)  # Default opacity
        
        # Arrow styling
        arrow_config = self.style_calculator.calculate_arrow_styles(
            data, config.get('show_arrows', False)
        )
        
        symbology = {
            'colors': colors,
            'line_widths': line_widths,
            'opacities': opacities,
            'class_breaks': class_breaks,
            'class_indices': class_indices,
            'arrow_config': arrow_config,
            'legend_config': {
                'title': config.get('legend_title', f'{metric_column.title()}'),
                'class_breaks': class_breaks,
                'colors': self.color_manager.get_color_palette(metric_type, n_classes),
                'outlier_caps': outlier_caps if config.get('show_outlier_caps', True) else None
            }
        }
        
        logger.info(f"Created symbology for {len(data)} features using {metric_column}")
        return symbology
    
    def classify_and_color_data(self, values, metric_type: str, method: str = 'quantiles', 
                               n_classes: int = 5) -> Tuple[List[float], List[str]]:
        """
        Convenience method to classify data and get colors.
        
        Args:
            values: Array of values to classify
            metric_type: Type of metric ('duration' or 'speed')
            method: Classification method
            n_classes: Number of classes
            
        Returns:
            Tuple of (class_breaks, colors)
        """
        import numpy as np
        
        # Convert to numpy array if needed
        if not isinstance(values, np.ndarray):
            values = np.array(values)
        
        # Classify data
        class_indices, class_breaks = self.classifier.classify_data(
            values, method, n_classes
        )
        
        # Get colors
        colors = self.color_manager.get_color_palette(metric_type, n_classes)
        
        return class_breaks, colors