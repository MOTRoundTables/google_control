"""
Tests for failed observations reference shapefile functionality.

Tests the create_failed_observations_reference_shapefile function which creates
a reference comparison shapefile for failed observations with timestamp aggregation.
"""

import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
import tempfile
import os
from pathlib import Path

from components.control.report import create_failed_observations_reference_shapefile


class TestFailedObservationsReferenceShapefile:
    """Test creation of reference comparison shapefile for failed observations."""

    def setup_method(self):
        """Set up test data."""
        # Create reference shapefile
        self.reference_shapefile = gpd.GeoDataFrame({
            'Id': ['1', '2'],
            'From': ['653', '655'],
            'To': ['655', '657'],
            'geometry': [
                LineString([(34.8, 32.1), (34.81, 32.11), (34.82, 32.12)]),
                LineString([(34.82, 32.12), (34.83, 32.13), (34.84, 32.14)])
            ]
        }, crs='EPSG:4326')

        # Create failed observations data with multiple alternatives per timestamp
        self.failed_observations = pd.DataFrame({
            'Name': ['s_653-655', 's_653-655', 's_653-655', 's_655-657', 's_655-657'],
            'link_id': ['s_653-655', 's_653-655', 's_653-655', 's_655-657', 's_655-657'],
            'timestamp': [
                '2025-07-01 13:45:00',
                '2025-07-01 13:45:00',  # Same timestamp, different alternative
                '2025-07-01 13:45:00',  # Same timestamp, different alternative
                '2025-07-01 14:00:00',
                '2025-07-01 14:15:00'
            ],
            'RouteAlternative': [1, 2, 3, 1, 1],
            'is_valid': [False, False, False, False, False],
            'valid_code': [2, 2, 2, 2, 2],
            'hausdorff_distance': [6.5, 12.3, 8.7, 15.2, 4.8],
            'hausdorff_pass': [False, False, False, False, False]
        })

        # Failed observations with length and coverage tests
        self.failed_observations_with_all_tests = pd.DataFrame({
            'Name': ['s_653-655', 's_653-655', 's_655-657'],
            'link_id': ['s_653-655', 's_653-655', 's_655-657'],
            'timestamp': [
                '2025-07-01 13:45:00',
                '2025-07-01 13:45:00',  # Same timestamp
                '2025-07-01 14:00:00'
            ],
            'RouteAlternative': [1, 2, 1],
            'is_valid': [False, False, False],
            'valid_code': [2, 2, 2],
            'hausdorff_distance': [6.5, 12.3, 15.2],
            'hausdorff_pass': [False, False, False],
            'length_ratio': [1.15, 0.85, 1.25],
            'length_pass': [False, False, False],
            'coverage_percent': [65.3, 72.1, 58.9],
            'coverage_pass': [False, False, False]
        })

    def test_basic_reference_shapefile_creation(self):
        """Test basic reference shapefile creation with timestamp aggregation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_reference.shp"

            create_failed_observations_reference_shapefile(
                self.failed_observations,
                self.reference_shapefile,
                str(output_path)
            )

            # Verify shapefile was created
            assert output_path.exists()

            # Load and verify content
            result_gdf = gpd.read_file(str(output_path))

            # Should have 3 rows: one for each unique (link_id, timestamp)
            assert len(result_gdf) == 3

            # Verify timestamp aggregation occurred
            timestamps = set(result_gdf['timestamp'])
            assert '2025-07-01 13:45:00' in timestamps  # 3 alternatives aggregated to 1 row
            assert '2025-07-01 14:00:00' in timestamps  # 1 alternative = 1 row
            assert '2025-07-01 14:15:00' in timestamps  # 1 alternative = 1 row

            # Verify link_ids
            link_ids = set(result_gdf['link_id'])
            assert 's_653-655' in link_ids
            assert 's_655-657' in link_ids

    def test_hausdorff_metrics_aggregation(self):
        """Test that Hausdorff metrics are properly aggregated."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_hausdorff.shp"

            create_failed_observations_reference_shapefile(
                self.failed_observations,
                self.reference_shapefile,
                str(output_path)
            )

            result_gdf = gpd.read_file(str(output_path))

            # Find the row with 3 alternatives (timestamp 13:45)
            multi_alt_row = result_gdf[result_gdf['timestamp'] == '2025-07-01 13:45:00'].iloc[0]

            # Verify aggregation: alternatives had distances [6.5, 12.3, 8.7]
            assert multi_alt_row['num_altern'] == 3  # Truncated field name
            assert abs(multi_alt_row['worst_haus'] - 12.3) < 0.1  # Max
            assert abs(multi_alt_row['best_hausd'] - 6.5) < 0.1   # Min
            assert abs(multi_alt_row['avg_hausdo'] - 9.17) < 0.1  # Average

    def test_length_and_coverage_metrics(self):
        """Test aggregation of length and coverage metrics when present."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_all_metrics.shp"

            create_failed_observations_reference_shapefile(
                self.failed_observations_with_all_tests,
                self.reference_shapefile,
                str(output_path)
            )

            result_gdf = gpd.read_file(str(output_path))

            # Find the multi-alternative row
            multi_alt_row = result_gdf[result_gdf['timestamp'] == '2025-07-01 13:45:00'].iloc[0]

            # Verify length metrics: [1.15, 0.85]
            assert abs(multi_alt_row['worst_leng'] - 1.15) < 0.01  # Max ratio
            assert abs(multi_alt_row['best_lengt'] - 0.85) < 0.01  # Min ratio
            assert abs(multi_alt_row['avg_length'] - 1.0) < 0.01   # Average

            # Verify coverage metrics: [65.3, 72.1] (lower is worse)
            assert abs(multi_alt_row['worst_cove'] - 65.3) < 0.1   # Min coverage (worst)
            assert abs(multi_alt_row['best_cover'] - 72.1) < 0.1   # Max coverage (best)
            assert abs(multi_alt_row['avg_covera'] - 68.7) < 0.1   # Average

    def test_reference_geometry_preservation(self):
        """Test that reference shapefile geometry is used correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_geometry.shp"

            create_failed_observations_reference_shapefile(
                self.failed_observations,
                self.reference_shapefile,
                str(output_path)
            )

            result_gdf = gpd.read_file(str(output_path))

            # Verify geometries match reference shapefile
            link_653_655_row = result_gdf[result_gdf['link_id'] == 's_653-655'].iloc[0]
            reference_653_655 = self.reference_shapefile[self.reference_shapefile['From'] == '653'].iloc[0]

            # Geometries should be identical (from reference shapefile)
            assert link_653_655_row.geometry.equals(reference_653_655.geometry)

    def test_crs_preservation(self):
        """Test that CRS is preserved from reference shapefile."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_crs.shp"

            create_failed_observations_reference_shapefile(
                self.failed_observations,
                self.reference_shapefile,
                str(output_path)
            )

            result_gdf = gpd.read_file(str(output_path))

            # CRS should match reference shapefile
            assert result_gdf.crs == self.reference_shapefile.crs

    def test_empty_failed_observations(self):
        """Test handling of empty failed observations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_empty.shp"

            empty_df = pd.DataFrame()

            create_failed_observations_reference_shapefile(
                empty_df,
                self.reference_shapefile,
                str(output_path)
            )

            # No shapefile should be created for empty input
            assert not output_path.exists()

    def test_missing_link_in_shapefile(self):
        """Test handling of failed observations for links not in shapefile."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_missing_link.shp"

            # Add failed observation for link not in shapefile
            failed_with_missing = self.failed_observations.copy()
            missing_row = pd.DataFrame({
                'Name': ['s_999-888'],
                'link_id': ['s_999-888'],
                'timestamp': ['2025-07-01 15:00:00'],
                'RouteAlternative': [1],
                'is_valid': [False],
                'valid_code': [2],
                'hausdorff_distance': [25.0],
                'hausdorff_pass': [False]
            })
            failed_with_missing = pd.concat([failed_with_missing, missing_row], ignore_index=True)

            create_failed_observations_reference_shapefile(
                failed_with_missing,
                self.reference_shapefile,
                str(output_path)
            )

            result_gdf = gpd.read_file(str(output_path))

            # Should only include links that exist in shapefile
            link_ids = set(result_gdf['link_id'])
            assert 's_999-888' not in link_ids
            assert 's_653-655' in link_ids

    def test_mixed_column_names(self):
        """Test handling of mixed column naming conventions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_mixed_names.shp"

            # Use different column name conventions
            mixed_df = pd.DataFrame({
                'Name': ['s_653-655'],  # Uppercase
                'Timestamp': ['2025-07-01 13:45:00'],  # Uppercase
                'RouteAlternative': [1],
                'is_valid': [False],
                'valid_code': [2],
                'hausdorff_distance': [6.5],
                'hausdorff_pass': [False]
            })

            create_failed_observations_reference_shapefile(
                mixed_df,
                self.reference_shapefile,
                str(output_path)
            )

            result_gdf = gpd.read_file(str(output_path))

            # Should handle column name normalization
            assert len(result_gdf) == 1
            assert result_gdf.iloc[0]['link_id'] == 's_653-655'