"""
Configuration management for map visualization.

This module extends the existing configuration system with map symbology
and visualization settings.
"""

import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MapSymbologyConfig:
    """Manages map symbology configuration settings."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "map_symbology_config.json"
        self.default_config = self._get_default_config()
        self.config = self._load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default map symbology configuration."""
        return {
            "map_symbology": {
                "duration": {
                    "palette": "RdYlGn_r",
                    "classification": "quantiles",
                    "n_classes": 5,
                    "outlier_caps": [2, 98],
                    "width_scale": [1, 8],
                    "opacity_scale": [0.3, 1.0],
                    "legend_title": "Duration (minutes)"
                },
                "speed": {
                    "palette": "RdYlGn",
                    "classification": "quantiles",
                    "n_classes": 5,
                    "outlier_caps": [2, 98],
                    "width_scale": [1, 8],
                    "opacity_scale": [0.3, 1.0],
                    "legend_title": "Speed (km/h)"
                }
            },
            "thresholds": {
                "free_flow_speed_kmh": 50,
                "max_acceptable_duration_sec": 1800,
                "min_observations_for_confidence": 10,
                "min_link_length_m": 10,
                "max_link_length_m": 10000
            },
            "default_paths": {
                "shapefile": "E:/google_agg/test_data/aggregation/google_results_to_golan_17_8_25/google_results_to_golan_17_8_25.shp",
                "export_directory": "./exports/maps/"
            },
            "map_settings": {
                "default_zoom": 10,
                "default_center": [31.5, 34.8],
                "target_crs": "EPSG:2039",
                "basemap_enabled": True,
                "arrows_enabled": False,
                "labels_enabled": False,
                "top_k_labels": 10
            },
            "performance": {
                "max_features_full_detail": 10000,
                "simplification_zoom_levels": {
                    "1": 0.1,
                    "5": 1.0,
                    "10": 5.0,
                    "15": 20.0
                },
                "cache_enabled": True,
                "progressive_loading": True
            }
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded map configuration from {self.config_path}")
                
                # Merge with defaults to ensure all keys exist
                merged_config = self._merge_configs(self.default_config, config)
                return merged_config
            except Exception as e:
                logger.error(f"Failed to load config from {self.config_path}: {e}")
                logger.info("Using default configuration")
                return self.default_config.copy()
        else:
            logger.info(f"Config file {self.config_path} not found, using defaults")
            return self.default_config.copy()
    
    def _merge_configs(self, default: Dict, user: Dict) -> Dict:
        """Recursively merge user config with defaults."""
        merged = default.copy()
        
        for key, value in user.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            # Ensure directory exists
            config_dir = Path(self.config_path).parent
            config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved map configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")
    
    def get_symbology_config(self, metric_type: str) -> Dict[str, Any]:
        """Get symbology configuration for specific metric type."""
        return self.config["map_symbology"].get(metric_type, self.config["map_symbology"]["duration"])
    
    def get_thresholds(self) -> Dict[str, Any]:
        """Get threshold configuration."""
        return self.config["thresholds"]
    
    def get_default_paths(self) -> Dict[str, str]:
        """Get default file paths."""
        return self.config["default_paths"]
    
    def get_map_settings(self) -> Dict[str, Any]:
        """Get map display settings."""
        return self.config["map_settings"]
    
    def get_performance_settings(self) -> Dict[str, Any]:
        """Get performance optimization settings."""
        return self.config["performance"]
    
    def update_symbology_config(self, metric_type: str, updates: Dict[str, Any]) -> None:
        """Update symbology configuration for specific metric type."""
        if metric_type not in self.config["map_symbology"]:
            self.config["map_symbology"][metric_type] = self.config["map_symbology"]["duration"].copy()
        
        self.config["map_symbology"][metric_type].update(updates)
        logger.info(f"Updated symbology config for {metric_type}")
    
    def update_thresholds(self, updates: Dict[str, Any]) -> None:
        """Update threshold configuration."""
        self.config["thresholds"].update(updates)
        logger.info("Updated threshold configuration")
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        self.config = self.default_config.copy()
        logger.info("Reset configuration to defaults")


class MapPresetManager:
    """Manages symbology presets for different analysis types."""
    
    def __init__(self, config: MapSymbologyConfig):
        self.config = config
        self.presets = self._get_default_presets()
    
    def _get_default_presets(self) -> Dict[str, Dict[str, Any]]:
        """Get default symbology presets."""
        return {
            "duration_focused": {
                "name": "Duration Analysis",
                "description": "Optimized for travel time analysis",
                "metric_type": "duration",
                "symbology": {
                    "palette": "RdYlGn_r",
                    "classification": "quantiles",
                    "n_classes": 7,
                    "outlier_caps": [5, 95],
                    "width_scale": [2, 10],
                    "opacity_scale": [0.4, 1.0],
                    "show_arrows": False,
                    "legend_title": "Travel Time (minutes)"
                }
            },
            "speed_focused": {
                "name": "Speed Analysis", 
                "description": "Optimized for speed and congestion analysis",
                "metric_type": "speed",
                "symbology": {
                    "palette": "RdYlGn",
                    "classification": "standard_deviation",
                    "n_classes": 5,
                    "outlier_caps": [2, 98],
                    "width_scale": [1, 6],
                    "opacity_scale": [0.3, 0.9],
                    "show_arrows": True,
                    "legend_title": "Speed (km/h)"
                }
            },
            "reliability_focused": {
                "name": "Reliability Analysis",
                "description": "Optimized for data quality and reliability assessment",
                "metric_type": "duration",
                "symbology": {
                    "palette": "viridis",
                    "classification": "quantiles",
                    "n_classes": 5,
                    "outlier_caps": [10, 90],
                    "width_scale": [1, 8],
                    "opacity_scale": [0.2, 1.0],  # Strong opacity variation for confidence
                    "show_arrows": False,
                    "legend_title": "Travel Time Reliability"
                }
            }
        }
    
    def get_preset(self, preset_name: str) -> Optional[Dict[str, Any]]:
        """Get specific preset configuration."""
        return self.presets.get(preset_name)
    
    def list_presets(self) -> List[str]:
        """Get list of available preset names."""
        return list(self.presets.keys())
    
    def apply_preset(self, preset_name: str) -> bool:
        """Apply preset to current configuration."""
        preset = self.get_preset(preset_name)
        if preset is None:
            logger.error(f"Preset {preset_name} not found")
            return False
        
        metric_type = preset["metric_type"]
        symbology = preset["symbology"]
        
        self.config.update_symbology_config(metric_type, symbology)
        logger.info(f"Applied preset {preset_name} for {metric_type}")
        return True
    
    def save_custom_preset(self, name: str, description: str, 
                          metric_type: str, symbology: Dict[str, Any]) -> None:
        """Save custom preset."""
        self.presets[name] = {
            "name": name,
            "description": description,
            "metric_type": metric_type,
            "symbology": symbology,
            "custom": True
        }
        logger.info(f"Saved custom preset {name}")


# Global configuration instance
_map_config = None

def get_map_config(config_path: Optional[str] = None) -> MapSymbologyConfig:
    """Get global map configuration instance."""
    global _map_config
    if _map_config is None:
        _map_config = MapSymbologyConfig(config_path)
    return _map_config

def get_preset_manager(config: Optional[MapSymbologyConfig] = None) -> MapPresetManager:
    """Get preset manager instance."""
    if config is None:
        config = get_map_config()
    return MapPresetManager(config)