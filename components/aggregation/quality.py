"""
Quality reporting interface for interactive map visualization.

This module implements warning tables for missing links and data issues,
quality metrics display in KPI strip, and quality filter toggles and indicators.
"""

import pandas as pd
import geopandas as gpd
import streamlit as st
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.icons import render_subheader_with_icon, render_icon_text, get_icon_for_component

logger = logging.getLogger(__name__)


class QualityReportingInterface:
    """
    Quality reporting interface for data quality visualization and interaction.
    
    Provides warning tables, quality metrics display, and filter toggles
    for comprehensive data quality management.
    """
    
    def __init__(self):
        self.quality_indicators = {
            'excellent': {'color': '#28a745', 'icon': 'EXCELLENT', 'threshold': 90},
            'good': {'color': '#17a2b8', 'icon': 'GOOD', 'threshold': 75},
            'moderate': {'color': '#ffc107', 'icon': 'MODERATE', 'threshold': 60},
            'poor': {'color': '#dc3545', 'icon': 'POOR', 'threshold': 0}
        }
    
    def render_quality_dashboard(self, quality_report: Dict[str, Any],
                               show_details: bool = True) -> None:
        """
        Render comprehensive quality dashboard in Streamlit.
        
        Args:
            quality_report: Quality report from DataQualityChecker
            show_details: Whether to show detailed quality sections
        """
        render_subheader_with_icon('analysis', 'Data Quality Dashboard')
        
        # Overall quality summary
        self._render_overall_quality_summary(quality_report)
        
        if show_details:
            # Quality metrics tabs
            tabs = st.tabs(["📈 Metrics", "⚠️ Issues", "🔗 Join Audit", "📋 Recommendations"])
            
            with tabs[0]:
                self._render_quality_metrics(quality_report)
            
            with tabs[1]:
                self._render_quality_issues(quality_report)
            
            with tabs[2]:
                self._render_join_audit(quality_report)
            
            with tabs[3]:
                self._render_recommendations(quality_report)
    
    def _render_overall_quality_summary(self, quality_report: Dict[str, Any]) -> None:
        """Render overall quality summary with key metrics."""
        overall_quality = quality_report.get('overall_quality', {})
        
        # Main quality indicator
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            quality_level = overall_quality.get('overall_level', 'unknown')
            quality_score = overall_quality.get('overall_score', 0)
            indicator = self.quality_indicators.get(quality_level, self.quality_indicators['poor'])
            
            st.markdown(f"""
            <div style="padding: 1rem; border-radius: 0.5rem; background-color: {indicator['color']}20; border-left: 4px solid {indicator['color']};">
                <h3 style="margin: 0; color: {indicator['color']};">
                    {indicator['icon']} Overall Quality: {quality_level.title()}
                </h3>
                <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem;">
                    Score: {quality_score:.1f}/100
                </p>
                <p style="margin: 0.25rem 0 0 0; font-size: 0.9rem; opacity: 0.8;">
                    {overall_quality.get('summary', 'No summary available')}
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        # Component quality scores
        component_scores = overall_quality.get('component_scores', {})
        
        with col2:
            speed_score = component_scores.get('speed', 0)
            speed_level = self._get_quality_level(speed_score)
            speed_indicator = self.quality_indicators[speed_level]
            st.metric(
                label="Speed Quality",
                value=f"{speed_score:.0f}/100",
                delta=None,
                help="Quality of speed data validation"
            )
            st.markdown(f"<div style='text-align: center; font-size: 1.5rem;'>{speed_indicator['icon']}</div>", 
                       unsafe_allow_html=True)
        
        with col3:
            duration_score = component_scores.get('duration', 0)
            duration_level = self._get_quality_level(duration_score)
            duration_indicator = self.quality_indicators[duration_level]
            st.metric(
                label="Duration Quality",
                value=f"{duration_score:.0f}/100",
                delta=None,
                help="Quality of duration data validation"
            )
            st.markdown(f"<div style='text-align: center; font-size: 1.5rem;'>{duration_indicator['icon']}</div>", 
                       unsafe_allow_html=True)
        
        with col4:
            obs_score = component_scores.get('observations', 0)
            obs_level = self._get_quality_level(obs_score)
            obs_indicator = self.quality_indicators[obs_level]
            st.metric(
                label="Observation Quality",
                value=f"{obs_score:.0f}/100",
                delta=None,
                help="Quality of observation count data"
            )
            st.markdown(f"<div style='text-align: center; font-size: 1.5rem;'>{obs_indicator['icon']}</div>", 
                       unsafe_allow_html=True)
    
    def _render_quality_metrics(self, quality_report: Dict[str, Any]) -> None:
        """Render detailed quality metrics with charts."""
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Speed Validation")
            speed_validation = quality_report.get('speed_validation', {})
            if speed_validation.get('has_speed_data', False):
                self._render_speed_metrics(speed_validation)
            else:
                st.warning("No speed data available for validation")
        
        with col2:
            st.subheader("Duration Validation")
            duration_validation = quality_report.get('duration_validation', {})
            if duration_validation.get('has_duration_data', False):
                self._render_duration_metrics(duration_validation)
            else:
                st.warning("No duration data available for validation")
        
        # Observation metrics
        st.subheader("Observation Analysis")
        obs_validation = quality_report.get('observation_validation', {})
        if obs_validation.get('has_observation_data', False):
            self._render_observation_metrics(obs_validation)
        else:
            st.warning("No observation count data available for validation")
    
    def _render_speed_metrics(self, speed_validation: Dict[str, Any]) -> None:
        """Render speed validation metrics and charts."""
        stats = speed_validation.get('statistics', {})
        
        if stats:
            # Basic statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Mean Speed", f"{stats.get('mean', 0):.1f} km/h")
            with col2:
                st.metric("Median Speed", f"{stats.get('median', 0):.1f} km/h")
            with col3:
                st.metric("Std Dev", f"{stats.get('std', 0):.1f} km/h")
            
            # Speed distribution chart
            if all(key in stats for key in ['min', 'q25', 'median', 'q75', 'max']):
                fig = go.Figure()
                fig.add_trace(go.Box(
                    q1=[stats['q25']],
                    median=[stats['median']],
                    q3=[stats['q75']],
                    lowerfence=[stats['min']],
                    upperfence=[stats['max']],
                    mean=[stats['mean']],
                    name="Speed Distribution",
                    boxpoints=False
                ))
                fig.update_layout(
                    title="Speed Distribution",
                    yaxis_title="Speed (km/h)",
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Issues summary
        issues = speed_validation.get('issues', [])
        if issues:
            st.warning(f"Found {len(issues)} speed validation issues:")
            for issue in issues:
                st.write(f"• {issue}")
    
    def _render_duration_metrics(self, duration_validation: Dict[str, Any]) -> None:
        """Render duration validation metrics and charts."""
        stats = duration_validation.get('statistics', {})
        
        if stats:
            # Basic statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Mean Duration", f"{stats.get('mean_minutes', 0):.1f} min")
            with col2:
                st.metric("Median Duration", f"{stats.get('median_minutes', 0):.1f} min")
            with col3:
                st.metric("Std Dev", f"{stats.get('std', 0)/60:.1f} min")
            
            # Duration distribution chart
            if all(key in stats for key in ['min', 'q25', 'median', 'q75', 'max']):
                # Convert to minutes for display
                fig = go.Figure()
                fig.add_trace(go.Box(
                    q1=[stats['q25']/60],
                    median=[stats['median']/60],
                    q3=[stats['q75']/60],
                    lowerfence=[stats['min']/60],
                    upperfence=[stats['max']/60],
                    mean=[stats['mean']/60],
                    name="Duration Distribution",
                    boxpoints=False
                ))
                fig.update_layout(
                    title="Duration Distribution",
                    yaxis_title="Duration (minutes)",
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Issues summary
        issues = duration_validation.get('issues', [])
        if issues:
            st.warning(f"Found {len(issues)} duration validation issues:")
            for issue in issues:
                st.write(f"• {issue}")
    
    def _render_observation_metrics(self, obs_validation: Dict[str, Any]) -> None:
        """Render observation validation metrics and charts."""
        stats = obs_validation.get('statistics', {})
        
        if stats:
            # Basic statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Observations", f"{stats.get('total_observations', 0):,}")
            with col2:
                st.metric("Mean per Link", f"{stats.get('mean', 0):.1f}")
            with col3:
                st.metric("Median per Link", f"{stats.get('median', 0):.1f}")
            with col4:
                st.metric("Max per Link", f"{stats.get('max', 0):,}")
            
            # Observation distribution chart
            if all(key in stats for key in ['min', 'q25', 'median', 'q75', 'max']):
                fig = go.Figure()
                fig.add_trace(go.Box(
                    q1=[stats['q25']],
                    median=[stats['median']],
                    q3=[stats['q75']],
                    lowerfence=[stats['min']],
                    upperfence=[stats['max']],
                    mean=[stats['mean']],
                    name="Observation Count Distribution",
                    boxpoints=False
                ))
                fig.update_layout(
                    title="Observation Count Distribution",
                    yaxis_title="Number of Observations",
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Sparse/critical links summary
        sparse_links = obs_validation.get('sparse_links', [])
        critical_links = obs_validation.get('critical_links', [])
        
        if sparse_links or critical_links:
            col1, col2 = st.columns(2)
            with col1:
                if critical_links:
                    st.error(f"Critical Links: {len(critical_links)} links with very few observations")
                    if st.expander("Show Critical Links"):
                        st.write(critical_links[:20])  # Show first 20
            
            with col2:
                if sparse_links:
                    st.warning(f"Sparse Links: {len(sparse_links)} links with limited observations")
                    if st.expander("Show Sparse Links"):
                        st.write(sparse_links[:20])  # Show first 20
    
    def _render_quality_issues(self, quality_report: Dict[str, Any]) -> None:
        """Render quality issues with detailed breakdown."""
        st.subheader("Quality Issues Summary")
        
        # Collect all issues
        all_issues = []
        
        for validation_type in ['speed_validation', 'duration_validation', 'observation_validation', 'geometry_validation']:
            validation_data = quality_report.get(validation_type, {})
            issues = validation_data.get('issues', [])
            quality_level = validation_data.get('quality_level', 'unknown')
            
            for issue in issues:
                all_issues.append({
                    'Category': validation_type.replace('_validation', '').title(),
                    'Issue': issue,
                    'Severity': self._get_issue_severity(issue),
                    'Quality Level': quality_level
                })
        
        if all_issues:
            issues_df = pd.DataFrame(all_issues)
            
            # Group by severity
            severity_counts = issues_df['Severity'].value_counts()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Critical Issues", severity_counts.get('Critical', 0), 
                         delta=None, delta_color="inverse")
            with col2:
                st.metric("Warning Issues", severity_counts.get('Warning', 0),
                         delta=None, delta_color="off")
            with col3:
                st.metric("Info Issues", severity_counts.get('Info', 0),
                         delta=None, delta_color="off")
            
            # Issues table
            st.subheader("Detailed Issues")
            
            # Add severity color coding
            def color_severity(val):
                if val == 'Critical':
                    return 'background-color: #ffebee'
                elif val == 'Warning':
                    return 'background-color: #fff3e0'
                else:
                    return 'background-color: #e8f5e8'
            
            styled_df = issues_df.style.applymap(color_severity, subset=['Severity'])
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.success("No quality issues detected! 🎉")
    
    def _render_join_audit(self, quality_report: Dict[str, Any]) -> None:
        """Render join audit results with missing data analysis."""
        join_audit = quality_report.get('join_audit', {})
        
        if not join_audit:
            st.warning("No join audit data available")
            return
        
        # Join success metrics
        join_analysis = join_audit.get('join_analysis', {})
        if join_analysis:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Shapefile Links", join_analysis.get('shapefile_keys_count', 0))
            with col2:
                st.metric("Results Links", join_analysis.get('results_keys_count', 0))
            with col3:
                st.metric("Successful Matches", join_analysis.get('successful_matches', 0))
            with col4:
                success_rate = join_analysis.get('join_success_rate', 0)
                st.metric("Success Rate", f"{success_rate:.1f}%")
        
        # Missing data analysis
        missing_data = join_audit.get('missing_data', {})
        if missing_data:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Missing in Shapefile")
                missing_in_shapefile = missing_data.get('results_links_not_in_shapefile', [])
                if missing_in_shapefile:
                    st.error(f"Found {len(missing_in_shapefile)} result links without geometry")
                    if st.expander("Show Missing Links"):
                        st.write(missing_in_shapefile[:50])  # Show first 50
                else:
                    st.success("All result links have corresponding geometry")
            
            with col2:
                st.subheader("Missing in Results")
                missing_in_results = missing_data.get('shapefile_links_not_in_results', [])
                if missing_in_results:
                    st.warning(f"Found {len(missing_in_results)} shapefile links without results")
                    if st.expander("Show Missing Links"):
                        st.write(missing_in_results[:50])  # Show first 50
                else:
                    st.success("All shapefile links have corresponding results")
        
        # Duplicate analysis
        duplicate_analysis = join_audit.get('duplicate_analysis', {})
        if duplicate_analysis and 'error' not in duplicate_analysis:
            st.subheader("Duplicate Analysis")
            
            total_duplicates = duplicate_analysis.get('total_duplicate_records', 0)
            if total_duplicates > 0:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Duplicate Records", total_duplicates)
                with col2:
                    st.metric("Links with Duplicates", duplicate_analysis.get('links_with_duplicates', 0))
                
                # Show sample duplicates
                sample_duplicates = duplicate_analysis.get('sample_duplicates', [])
                if sample_duplicates:
                    st.subheader("Sample Duplicate Records")
                    st.dataframe(pd.DataFrame(sample_duplicates), use_container_width=True)
            else:
                st.success("No duplicate records found")
    
    def _render_recommendations(self, quality_report: Dict[str, Any]) -> None:
        """Render quality improvement recommendations."""
        join_audit = quality_report.get('join_audit', {})
        recommendations = join_audit.get('recommendations', [])
        
        if recommendations:
            st.subheader("Quality Improvement Recommendations")
            
            for i, recommendation in enumerate(recommendations, 1):
                st.info(f"**{i}.** {recommendation}")
        else:
            st.success("No specific recommendations - data quality looks good!")
        
        # Additional general recommendations based on quality scores
        overall_quality = quality_report.get('overall_quality', {})
        overall_score = overall_quality.get('overall_score', 0)
        
        if overall_score < 75:
            st.subheader("General Quality Improvement Suggestions")
            
            suggestions = []
            
            # Speed-specific suggestions
            speed_validation = quality_report.get('speed_validation', {})
            if speed_validation.get('quality_score', 100) < 75:
                suggestions.append("Review speed calculation methodology and data collection procedures")
                suggestions.append("Consider implementing speed validation rules during data collection")
            
            # Duration-specific suggestions
            duration_validation = quality_report.get('duration_validation', {})
            if duration_validation.get('quality_score', 100) < 75:
                suggestions.append("Review duration calculation methodology and outlier handling")
                suggestions.append("Consider implementing duration validation rules during processing")
            
            # Observation-specific suggestions
            obs_validation = quality_report.get('observation_validation', {})
            if obs_validation.get('quality_score', 100) < 75:
                suggestions.append("Increase data collection frequency for links with sparse observations")
                suggestions.append("Consider longer collection periods for more reliable statistics")
            
            for suggestion in suggestions:
                st.write(f"• {suggestion}")
    
    def render_quality_filter_controls(self, quality_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render quality filter controls and return filter settings.
        
        Args:
            quality_report: Quality report from DataQualityChecker
            
        Returns:
            Dictionary with quality filter settings
        """
        render_subheader_with_icon('filters', 'Quality Filters')
        
        filter_settings = {}
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Observation Quality**")
            
            # Sparse observation filter
            obs_validation = quality_report.get('observation_validation', {})
            if obs_validation.get('has_observation_data', False):
                filter_sparse = st.checkbox(
                    "Filter out sparse observations",
                    value=False,
                    help="Remove links with very few observations for more reliable analysis"
                )
                
                if filter_sparse:
                    min_obs = st.slider(
                        "Minimum observations per link",
                        min_value=1,
                        max_value=50,
                        value=10,
                        help="Links with fewer observations will be filtered out"
                    )
                    filter_settings['min_observations'] = min_obs
                else:
                    filter_settings['min_observations'] = None
            
            # Critical links filter
            critical_links = obs_validation.get('critical_links', [])
            if critical_links:
                filter_critical = st.checkbox(
                    f"Filter out critical links ({len(critical_links)} links)",
                    value=False,
                    help="Remove links with critically low observation counts"
                )
                filter_settings['filter_critical'] = filter_critical
        
        with col2:
            st.write("**Value Quality**")
            
            # Speed quality filter
            speed_validation = quality_report.get('speed_validation', {})
            if speed_validation.get('has_speed_data', False):
                filter_invalid_speeds = st.checkbox(
                    "Filter out invalid speeds",
                    value=False,
                    help="Remove records with non-positive or extreme speed values"
                )
                filter_settings['filter_invalid_speeds'] = filter_invalid_speeds
            
            # Duration quality filter
            duration_validation = quality_report.get('duration_validation', {})
            if duration_validation.get('has_duration_data', False):
                filter_invalid_durations = st.checkbox(
                    "Filter out invalid durations",
                    value=False,
                    help="Remove records with non-positive or extreme duration values"
                )
                filter_settings['filter_invalid_durations'] = filter_invalid_durations
        
        return filter_settings
    
    def render_quality_kpi_strip(self, quality_report: Dict[str, Any]) -> None:
        """
        Render quality metrics in KPI strip format.
        
        Args:
            quality_report: Quality report from DataQualityChecker
        """
        overall_quality = quality_report.get('overall_quality', {})
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            quality_score = overall_quality.get('overall_score', 0)
            quality_level = overall_quality.get('overall_level', 'unknown')
            indicator = self.quality_indicators.get(quality_level, self.quality_indicators['poor'])
            
            st.metric(
                label="Data Quality",
                value=f"{quality_score:.0f}/100",
                delta=None,
                help=f"Overall data quality: {quality_level}"
            )
            st.markdown(f"<div style='text-align: center; font-size: 1.2rem;'>{indicator['icon']}</div>", 
                       unsafe_allow_html=True)
        
        with col2:
            speed_validation = quality_report.get('speed_validation', {})
            speed_issues = len(speed_validation.get('issues', []))
            st.metric(
                label="Speed Issues",
                value=speed_issues,
                delta=None,
                help="Number of speed validation issues found"
            )
        
        with col3:
            duration_validation = quality_report.get('duration_validation', {})
            duration_issues = len(duration_validation.get('issues', []))
            st.metric(
                label="Duration Issues",
                value=duration_issues,
                delta=None,
                help="Number of duration validation issues found"
            )
        
        with col4:
            obs_validation = quality_report.get('observation_validation', {})
            sparse_count = len(obs_validation.get('sparse_links', []))
            st.metric(
                label="Sparse Links",
                value=sparse_count,
                delta=None,
                help="Number of links with sparse observations"
            )
        
        with col5:
            join_audit = quality_report.get('join_audit', {})
            join_analysis = join_audit.get('join_analysis', {})
            success_rate = join_analysis.get('join_success_rate', 0)
            st.metric(
                label="Join Success",
                value=f"{success_rate:.0f}%",
                delta=None,
                help="Percentage of successful data joins"
            )
    
    def create_quality_warning_table(self, quality_report: Dict[str, Any]) -> pd.DataFrame:
        """
        Create warning table for missing links and data issues.
        
        Args:
            quality_report: Quality report from DataQualityChecker
            
        Returns:
            DataFrame with warning information
        """
        warnings = []
        
        # Join audit warnings
        join_audit = quality_report.get('join_audit', {})
        missing_data = join_audit.get('missing_data', {})
        
        if missing_data:
            missing_in_shapefile = missing_data.get('results_links_not_in_shapefile', [])
            missing_in_results = missing_data.get('shapefile_links_not_in_results', [])
            
            if missing_in_shapefile:
                warnings.append({
                    'Category': 'Missing Geometry',
                    'Issue': f'{len(missing_in_shapefile)} result links have no shapefile geometry',
                    'Severity': 'High',
                    'Count': len(missing_in_shapefile),
                    'Action': 'Update shapefile or verify link_id format'
                })
            
            if missing_in_results:
                warnings.append({
                    'Category': 'Missing Results',
                    'Issue': f'{len(missing_in_results)} shapefile links have no result data',
                    'Severity': 'Medium',
                    'Count': len(missing_in_results),
                    'Action': 'Extend data collection or verify processing'
                })
        
        # Quality validation warnings
        for validation_type, category in [
            ('speed_validation', 'Speed Quality'),
            ('duration_validation', 'Duration Quality'),
            ('observation_validation', 'Observation Quality'),
            ('geometry_validation', 'Geometry Quality')
        ]:
            validation_data = quality_report.get(validation_type, {})
            issues = validation_data.get('issues', [])
            
            for issue in issues:
                severity = self._get_issue_severity(issue)
                warnings.append({
                    'Category': category,
                    'Issue': issue,
                    'Severity': severity,
                    'Count': self._extract_count_from_issue(issue),
                    'Action': self._get_suggested_action(issue, category)
                })
        
        return pd.DataFrame(warnings) if warnings else pd.DataFrame(columns=['Category', 'Issue', 'Severity', 'Count', 'Action'])
    
    def _get_quality_level(self, score: float) -> str:
        """Get quality level based on score."""
        for level, config in self.quality_indicators.items():
            if score >= config['threshold']:
                return level
        return 'poor'
    
    def _get_issue_severity(self, issue: str) -> str:
        """Determine issue severity based on issue text."""
        issue_lower = issue.lower()
        
        if any(word in issue_lower for word in ['non-positive', 'invalid', 'critical', 'null']):
            return 'Critical'
        elif any(word in issue_lower for word in ['extreme', 'duplicate', 'missing']):
            return 'Warning'
        else:
            return 'Info'
    
    def _extract_count_from_issue(self, issue: str) -> int:
        """Extract count number from issue text."""
        import re
        match = re.search(r'Found (\d+)', issue)
        return int(match.group(1)) if match else 0
    
    def _get_suggested_action(self, issue: str, category: str) -> str:
        """Get suggested action based on issue and category."""
        issue_lower = issue.lower()
        
        if 'non-positive' in issue_lower:
            return 'Review data collection and calculation methods'
        elif 'extreme' in issue_lower:
            return 'Investigate outliers and consider data validation rules'
        elif 'sparse' in issue_lower or 'critical' in issue_lower:
            return 'Increase observation frequency or extend collection period'
        elif 'missing' in issue_lower:
            return 'Verify data completeness and join key format'
        elif 'duplicate' in issue_lower:
            return 'Remove duplicates before analysis'
        else:
            return 'Review data quality procedures'