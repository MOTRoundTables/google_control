"""
Control Component - Dataset validation and reporting functionality.

This component provides comprehensive validation of Google Maps polyline data
against reference shapefiles using geometric similarity metrics.
"""

from .page import control_page
from .validator import (
    validate_dataframe_batch,
    ValidationParameters,
    ValidCode
)
from .report import (
    generate_link_report,
    write_shapefile_with_results
)

__all__ = [
    'control_page',
    'validate_dataframe_batch',
    'ValidationParameters',
    'ValidCode',
    'generate_link_report',
    'write_shapefile_with_results'
]
