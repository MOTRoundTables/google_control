"""
Professional icon utilities for the Google Maps Link Monitoring system.
Provides consistent icon styling across all components using streamlit-option-menu icons.
"""

import streamlit as st

# Try to import streamlit-option-menu for professional icons
try:
    from streamlit_option_menu import option_menu
    HAS_OPTION_MENU = True
except ImportError:
    HAS_OPTION_MENU = False


def render_icon_header(icon_name: str, text: str, level: int = 1, color: str = "#0068c9") -> None:
    """
    Render a professional header with Bootstrap icon.

    Args:
        icon_name: Bootstrap icon name (e.g., 'shield-check', 'clock', etc.)
        text: Header text
        level: Header level (1-6)
        color: Icon color (default blue)
    """
    if not HAS_OPTION_MENU:
        # Fallback to emoji headers
        emoji_map = {
            'shield-check': '🛡️',
            'clock': '⏰',
            'activity': '📊',
            'map': '🗺️',
            'tools': '🔧',
            'book': '📚',
            'file-text': '📄',
            'folder': '📁',
            'folder-open': '📂',
            'gear': '⚙️',
            'target': '🎯',
            'play': '🚀',
            'calendar': '📅',
            'settings': '⚙️',
            'filter': '🔍',
            'bar-chart': '📊',
            'map-pin': '📍',
            'pause': '⏸️',
            'info': 'ℹ️'
        }
        emoji = emoji_map.get(icon_name, '📄')
        if level == 1:
            st.title(f"{emoji} {text}")
        elif level == 2:
            st.header(f"{emoji} {text}")
        elif level == 3:
            st.subheader(f"{emoji} {text}")
        else:
            st.markdown(f"{'#' * level} {emoji} {text}")
        return

    # Professional Bootstrap icon header
    icon_size = {1: 32, 2: 24, 3: 20, 4: 18, 5: 16, 6: 14}.get(level, 20)

    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1rem;">
        <i class="bi bi-{icon_name}" style="font-size: {icon_size}px; color: {color}; margin-right: 12px;"></i>
        <h{level} style="margin: 0;">{text}</h{level}>
    </div>
    """, unsafe_allow_html=True)


def render_icon_text(icon_name: str, text: str, size: int = 16, color: str = "#0068c9") -> None:
    """
    Render text with a Bootstrap icon inline.

    Args:
        icon_name: Bootstrap icon name
        text: Text to display
        size: Icon size in pixels
        color: Icon color
    """
    if not HAS_OPTION_MENU:
        # Fallback to emoji
        emoji_map = {
            'shield-check': '🛡️',
            'clock': '⏰',
            'activity': '📊',
            'map': '🗺️',
            'tools': '🔧',
            'book': '📚',
            'file-text': '📄',
            'folder': '📁',
            'folder-open': '📂',
            'gear': '⚙️',
            'target': '🎯',
            'play': '🚀',
            'calendar': '📅',
            'settings': '⚙️',
            'filter': '🔍',
            'bar-chart': '📊',
            'map-pin': '📍',
            'pause': '⏸️',
            'info': 'ℹ️'
        }
        emoji = emoji_map.get(icon_name, '📄')
        st.markdown(f"**{emoji} {text}**")
        return

    # Professional Bootstrap icon text
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
        <i class="bi bi-{icon_name}" style="font-size: {size}px; color: {color}; margin-right: 8px;"></i>
        <strong>{text}</strong>
    </div>
    """, unsafe_allow_html=True)


def render_title_with_icon(icon_name: str, title: str) -> None:
    """Render a page title with professional icon."""
    render_icon_header(icon_name, title, level=1)


def render_header_with_icon(icon_name: str, header: str) -> None:
    """Render a section header with professional icon."""
    render_icon_header(icon_name, header, level=2)


def render_subheader_with_icon(icon_name: str, subheader: str) -> None:
    """Render a subsection header with professional icon."""
    render_icon_header(icon_name, subheader, level=3)


# Icon mapping for consistent usage across components
COMPONENT_ICONS = {
    # Navigation
    'dataset_control': 'shield-check',
    'hour_aggregation': 'clock',
    'hour_results': 'activity',
    'maps': 'map',
    'control_methodology': 'tools',
    'hour_methodology': 'book',

    # File operations
    'file_input': 'folder',
    'file_upload': 'folder-open',
    'download': 'download',

    # Configuration
    'configuration': 'gear',
    'settings': 'settings',
    'validation': 'shield-check',
    'parameters': 'target',

    # Data operations
    'processing': 'play',
    'results': 'activity',
    'analysis': 'bar-chart',
    'statistics': 'bar-chart',

    # Maps and spatial
    'map_view': 'map',
    'spatial': 'map-pin',
    'location': 'map-pin',

    # Time operations
    'timestamp': 'clock',
    'calendar': 'calendar',
    'time_filters': 'clock',

    # Quality and validation
    'quality': 'shield-check',
    'validation_tests': 'target',
    'report': 'file-text',

    # Controls
    'controls': 'gear',
    'filters': 'filter',
    'advanced': 'tools',
    'debug': 'info',
    'status': 'info'
}


def get_icon_for_component(component_key: str) -> str:
    """Get the appropriate icon name for a component."""
    return COMPONENT_ICONS.get(component_key, 'file-text')