"""
Link details panel for displaying detailed information about clicked links.

This module provides interactive panels with statistics, charts, and detailed
information for selected network links.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class LinkDetailsPanel:
    """Panel for displaying detailed link information and statistics."""
    
    def __init__(self):
        self.chart_height = 300
        self.sparkline_height = 150
    
    def render_link_details(self, link_data: pd.Series, 
                           hourly_data: Optional[pd.DataFrame] = None,
                           context: Dict[str, Any] = None) -> None:
        """
        Render detailed link information panel.
        
        Args:
            link_data: Series with link information and current metrics
            hourly_data: Optional DataFrame with hourly data for the link
            context: Additional context information (date range, filters, etc.)
        """
        if link_data.empty:
            st.warning("⚠️ No link data available")
            return
        
        # Extract basic link information
        link_id = link_data.get('Id', link_data.get('link_id', 'N/A'))
        from_node = link_data.get('From', 'N/A')
        to_node = link_data.get('To', 'N/A')
        
        # Header
        st.subheader(f"🔗 Link Details: {link_id}")
        st.markdown(f"**Route:** {from_node} → {to_node}")
        
        # Basic information section
        self._render_basic_info(link_data)
        
        # Current metrics section
        self._render_current_metrics(link_data, context)
        
        # Statistical analysis section
        if hourly_data is not None and not hourly_data.empty:
            self._render_statistical_analysis(link_data, hourly_data, context)
            
            # Hourly profile charts
            self._render_hourly_profile(hourly_data, context)
            
            # Distribution histograms
            self._render_distribution_charts(hourly_data, context)
        else:
            st.info("📊 **Hourly profile data not available** - showing current metrics only")
    
    def _render_basic_info(self, link_data: pd.Series) -> None:
        """Render basic link information."""
        st.markdown("### 📋 Basic Information")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Link geometry info
            if 'length_m' in link_data and pd.notna(link_data['length_m']):
                length_km = link_data['length_m'] / 1000
                st.metric("Length", f"{length_km:.2f} km")
            
            # Observation count
            if 'n_valid' in link_data and pd.notna(link_data['n_valid']):
                n_obs = int(link_data['n_valid'])
                st.metric("Observations", f"{n_obs:,}")
        
        with col2:
            # Date context if available
            if 'date' in link_data and pd.notna(link_data['date']):
                st.metric("Date", str(link_data['date']))
            
            # Hour context if available
            if 'hour' in link_data and pd.notna(link_data['hour']):
                hour = int(link_data['hour'])
                st.metric("Hour", f"{hour:02d}:00")
        
        with col3:
            # Link ID components
            st.metric("From Node", str(link_data.get('From', 'N/A')))
            st.metric("To Node", str(link_data.get('To', 'N/A')))
    
    def _render_current_metrics(self, link_data: pd.Series, 
                               context: Dict[str, Any] = None) -> None:
        """Render current traffic metrics."""
        st.markdown("### 🚗 Current Traffic Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Average speed
            if 'avg_speed_kmh' in link_data and pd.notna(link_data['avg_speed_kmh']):
                speed = link_data['avg_speed_kmh']
                speed_delta = None
                
                # Add context comparison if available
                if context and 'reference_speed' in context:
                    speed_delta = speed - context['reference_speed']
                
                st.metric(
                    "Average Speed", 
                    f"{speed:.1f} km/h",
                    delta=f"{speed_delta:+.1f} km/h" if speed_delta is not None else None
                )
        
        with col2:
            # Average duration
            if 'avg_duration_sec' in link_data and pd.notna(link_data['avg_duration_sec']):
                duration_min = link_data['avg_duration_sec'] / 60
                duration_delta = None
                
                # Add context comparison if available
                if context and 'reference_duration' in context:
                    duration_delta = duration_min - (context['reference_duration'] / 60)
                
                st.metric(
                    "Average Duration", 
                    f"{duration_min:.1f} min",
                    delta=f"{duration_delta:+.1f} min" if duration_delta is not None else None
                )
        
        with col3:
            # Free flow time (if length available)
            if ('length_m' in link_data and 'avg_speed_kmh' in link_data and 
                pd.notna(link_data['length_m']) and pd.notna(link_data['avg_speed_kmh'])):
                
                length_km = link_data['length_m'] / 1000
                speed_kmh = link_data['avg_speed_kmh']
                
                if speed_kmh > 0:
                    free_flow_time = (length_km / speed_kmh) * 60  # minutes
                    st.metric("Free Flow Time", f"{free_flow_time:.1f} min")
        
        with col4:
            # Data quality indicator
            if 'n_valid' in link_data and pd.notna(link_data['n_valid']):
                n_obs = int(link_data['n_valid'])
                
                if n_obs >= 20:
                    quality = "Excellent"
                    quality_color = "🟢"
                elif n_obs >= 10:
                    quality = "Good"
                    quality_color = "🟡"
                elif n_obs >= 5:
                    quality = "Fair"
                    quality_color = "🟠"
                else:
                    quality = "Poor"
                    quality_color = "🔴"
                
                st.metric("Data Quality", f"{quality_color} {quality}")
    
    def _render_statistical_analysis(self, link_data: pd.Series, 
                                   hourly_data: pd.DataFrame,
                                   context: Dict[str, Any] = None) -> None:
        """Render statistical analysis of the link data."""
        st.markdown("### 📊 Statistical Analysis")
        
        # Calculate statistics from hourly data
        stats = self._calculate_link_statistics(hourly_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Duration Statistics (minutes)**")
            
            if 'duration_stats' in stats:
                dur_stats = stats['duration_stats']
                
                # Create metrics for duration
                st.metric("Mean", f"{dur_stats['mean']:.1f} min")
                st.metric("Median", f"{dur_stats['median']:.1f} min")
                st.metric("Std Dev", f"{dur_stats['std']:.1f} min")
                
                # Percentiles
                st.markdown("**Percentiles:**")
                st.write(f"• P10: {dur_stats['p10']:.1f} min")
                st.write(f"• P25: {dur_stats['p25']:.1f} min")
                st.write(f"• P75: {dur_stats['p75']:.1f} min")
                st.write(f"• P90: {dur_stats['p90']:.1f} min")
        
        with col2:
            st.markdown("**Speed Statistics (km/h)**")
            
            if 'speed_stats' in stats:
                speed_stats = stats['speed_stats']
                
                # Create metrics for speed
                st.metric("Mean", f"{speed_stats['mean']:.1f} km/h")
                st.metric("Median", f"{speed_stats['median']:.1f} km/h")
                st.metric("Std Dev", f"{speed_stats['std']:.1f} km/h")
                
                # Percentiles
                st.markdown("**Percentiles:**")
                st.write(f"• P10: {speed_stats['p10']:.1f} km/h")
                st.write(f"• P25: {speed_stats['p25']:.1f} km/h")
                st.write(f"• P75: {speed_stats['p75']:.1f} km/h")
                st.write(f"• P90: {speed_stats['p90']:.1f} km/h")
    
    def _render_hourly_profile(self, hourly_data: pd.DataFrame,
                              context: Dict[str, Any] = None) -> None:
        """Render hourly profile sparkline and detailed chart."""
        st.markdown("### 📈 Hourly Profile")
        
        if 'hour' not in hourly_data.columns:
            st.warning("⚠️ Hour column not available for hourly profile")
            return
        
        # Group by hour and calculate means
        hourly_profile = hourly_data.groupby('hour').agg({
            'avg_duration_sec': 'mean',
            'avg_speed_kmh': 'mean',
            'n_valid': 'sum'
        }).reset_index()
        
        # Convert duration to minutes
        hourly_profile['avg_duration_min'] = hourly_profile['avg_duration_sec'] / 60
        
        # Create tabs for different views
        tab1, tab2 = st.tabs(["📊 Duration Profile", "🚗 Speed Profile"])
        
        with tab1:
            # Duration profile chart
            fig_duration = go.Figure()
            
            fig_duration.add_trace(go.Scatter(
                x=hourly_profile['hour'],
                y=hourly_profile['avg_duration_min'],
                mode='lines+markers',
                name='Average Duration',
                line=dict(color='#e74c3c', width=3),
                marker=dict(size=6),
                hovertemplate='<b>Hour %{x}:00</b><br>Duration: %{y:.1f} min<extra></extra>'
            ))
            
            fig_duration.update_layout(
                title="Average Duration by Hour",
                xaxis_title="Hour of Day",
                yaxis_title="Duration (minutes)",
                height=self.chart_height,
                showlegend=False,
                hovermode='x unified'
            )
            
            # Add hour range markers if available in context
            if context and 'hour_range' in context:
                hour_start, hour_end = context['hour_range']
                fig_duration.add_vrect(
                    x0=hour_start, x1=hour_end,
                    fillcolor="rgba(0,100,80,0.2)",
                    layer="below", line_width=0,
                    annotation_text="Selected Range"
                )
            
            st.plotly_chart(fig_duration, use_container_width=True)
        
        with tab2:
            # Speed profile chart
            fig_speed = go.Figure()
            
            fig_speed.add_trace(go.Scatter(
                x=hourly_profile['hour'],
                y=hourly_profile['avg_speed_kmh'],
                mode='lines+markers',
                name='Average Speed',
                line=dict(color='#3498db', width=3),
                marker=dict(size=6),
                hovertemplate='<b>Hour %{x}:00</b><br>Speed: %{y:.1f} km/h<extra></extra>'
            ))
            
            fig_speed.update_layout(
                title="Average Speed by Hour",
                xaxis_title="Hour of Day",
                yaxis_title="Speed (km/h)",
                height=self.chart_height,
                showlegend=False,
                hovermode='x unified'
            )
            
            # Add hour range markers if available in context
            if context and 'hour_range' in context:
                hour_start, hour_end = context['hour_range']
                fig_speed.add_vrect(
                    x0=hour_start, x1=hour_end,
                    fillcolor="rgba(0,100,80,0.2)",
                    layer="below", line_width=0,
                    annotation_text="Selected Range"
                )
            
            st.plotly_chart(fig_speed, use_container_width=True)
        
        # Sparkline summary
        with st.expander("📊 Quick Summary", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                peak_hour = hourly_profile.loc[hourly_profile['avg_duration_min'].idxmax(), 'hour']
                peak_duration = hourly_profile['avg_duration_min'].max()
                st.metric("Peak Duration", f"Hour {int(peak_hour)}", f"{peak_duration:.1f} min")
            
            with col2:
                fastest_hour = hourly_profile.loc[hourly_profile['avg_speed_kmh'].idxmax(), 'hour']
                max_speed = hourly_profile['avg_speed_kmh'].max()
                st.metric("Fastest Hour", f"Hour {int(fastest_hour)}", f"{max_speed:.1f} km/h")
            
            with col3:
                total_obs = hourly_profile['n_valid'].sum()
                avg_obs_per_hour = total_obs / len(hourly_profile) if len(hourly_profile) > 0 else 0
                st.metric("Total Observations", f"{int(total_obs)}", f"{avg_obs_per_hour:.1f}/hour")
    
    def _render_distribution_charts(self, hourly_data: pd.DataFrame,
                                   context: Dict[str, Any] = None) -> None:
        """Render distribution histograms for speed and duration."""
        st.markdown("### 📊 Distribution Analysis")
        
        tab1, tab2 = st.tabs(["⏱️ Duration Distribution", "🚗 Speed Distribution"])
        
        with tab1:
            if 'avg_duration_sec' in hourly_data.columns:
                duration_min = hourly_data['avg_duration_sec'] / 60
                
                fig_hist_dur = px.histogram(
                    x=duration_min,
                    nbins=20,
                    title="Duration Distribution",
                    labels={'x': 'Duration (minutes)', 'y': 'Frequency'},
                    color_discrete_sequence=['#e74c3c']
                )
                
                # Add mean and median lines
                mean_dur = duration_min.mean()
                median_dur = duration_min.median()
                
                fig_hist_dur.add_vline(
                    x=mean_dur, line_dash="dash", line_color="blue",
                    annotation_text=f"Mean: {mean_dur:.1f} min"
                )
                fig_hist_dur.add_vline(
                    x=median_dur, line_dash="dash", line_color="green",
                    annotation_text=f"Median: {median_dur:.1f} min"
                )
                
                fig_hist_dur.update_layout(height=self.chart_height)
                st.plotly_chart(fig_hist_dur, use_container_width=True)
                
                # Distribution statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Skewness", f"{duration_min.skew():.2f}")
                with col2:
                    st.metric("Kurtosis", f"{duration_min.kurtosis():.2f}")
                with col3:
                    cv = duration_min.std() / duration_min.mean() if duration_min.mean() > 0 else 0
                    st.metric("Coeff. of Variation", f"{cv:.2f}")
        
        with tab2:
            if 'avg_speed_kmh' in hourly_data.columns:
                speed_data = hourly_data['avg_speed_kmh']
                
                fig_hist_speed = px.histogram(
                    x=speed_data,
                    nbins=20,
                    title="Speed Distribution",
                    labels={'x': 'Speed (km/h)', 'y': 'Frequency'},
                    color_discrete_sequence=['#3498db']
                )
                
                # Add mean and median lines
                mean_speed = speed_data.mean()
                median_speed = speed_data.median()
                
                fig_hist_speed.add_vline(
                    x=mean_speed, line_dash="dash", line_color="blue",
                    annotation_text=f"Mean: {mean_speed:.1f} km/h"
                )
                fig_hist_speed.add_vline(
                    x=median_speed, line_dash="dash", line_color="green",
                    annotation_text=f"Median: {median_speed:.1f} km/h"
                )
                
                fig_hist_speed.update_layout(height=self.chart_height)
                st.plotly_chart(fig_hist_speed, use_container_width=True)
                
                # Distribution statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Skewness", f"{speed_data.skew():.2f}")
                with col2:
                    st.metric("Kurtosis", f"{speed_data.kurtosis():.2f}")
                with col3:
                    cv = speed_data.std() / speed_data.mean() if speed_data.mean() > 0 else 0
                    st.metric("Coeff. of Variation", f"{cv:.2f}")
    
    def _calculate_link_statistics(self, hourly_data: pd.DataFrame) -> Dict[str, Dict]:
        """Calculate comprehensive statistics for the link."""
        stats = {}
        
        # Duration statistics
        if 'avg_duration_sec' in hourly_data.columns:
            duration_min = hourly_data['avg_duration_sec'] / 60
            stats['duration_stats'] = {
                'mean': duration_min.mean(),
                'median': duration_min.median(),
                'std': duration_min.std(),
                'min': duration_min.min(),
                'max': duration_min.max(),
                'p10': duration_min.quantile(0.1),
                'p25': duration_min.quantile(0.25),
                'p75': duration_min.quantile(0.75),
                'p90': duration_min.quantile(0.9)
            }
        
        # Speed statistics
        if 'avg_speed_kmh' in hourly_data.columns:
            speed_data = hourly_data['avg_speed_kmh']
            stats['speed_stats'] = {
                'mean': speed_data.mean(),
                'median': speed_data.median(),
                'std': speed_data.std(),
                'min': speed_data.min(),
                'max': speed_data.max(),
                'p10': speed_data.quantile(0.1),
                'p25': speed_data.quantile(0.25),
                'p75': speed_data.quantile(0.75),
                'p90': speed_data.quantile(0.9)
            }
        
        return stats


def render_link_details_sidebar(selected_link_id: str, 
                               all_data: pd.DataFrame,
                               context: Dict[str, Any] = None) -> None:
    """
    Render link details in sidebar for selected link.
    
    Args:
        selected_link_id: ID of the selected link
        all_data: Complete dataset with all links and time periods
        context: Context information (filters, date range, etc.)
    """
    if not selected_link_id:
        st.sidebar.info("👆 Click on a link in the map to see detailed information")
        return
    
    # Filter data for selected link
    link_data = all_data[all_data['link_id'] == selected_link_id]
    
    if link_data.empty:
        st.sidebar.warning(f"⚠️ No data found for link {selected_link_id}")
        return
    
    # Create details panel
    details_panel = LinkDetailsPanel()
    
    with st.sidebar:
        st.markdown("---")
        
        # Get current link info (latest or aggregated)
        current_link = link_data.iloc[0] if len(link_data) == 1 else link_data.mean(numeric_only=True)
        
        # Render details
        details_panel.render_link_details(
            link_data=current_link,
            hourly_data=link_data,
            context=context
        )


if __name__ == "__main__":
    # For testing purposes
    st.title("Link Details Panel Test")
    
    # Create sample data
    sample_link = pd.Series({
        'Id': 'TEST_001',
        'From': 'Node_A',
        'To': 'Node_B',
        'length_m': 1500,
        'avg_speed_kmh': 35.5,
        'avg_duration_sec': 152,
        'n_valid': 25,
        'date': '2025-01-15',
        'hour': 8
    })
    
    # Create sample hourly data
    sample_hourly = pd.DataFrame({
        'hour': range(24),
        'avg_duration_sec': np.random.normal(150, 30, 24),
        'avg_speed_kmh': np.random.normal(35, 8, 24),
        'n_valid': np.random.randint(10, 50, 24)
    })
    
    # Test the panel
    panel = LinkDetailsPanel()
    panel.render_link_details(sample_link, sample_hourly)