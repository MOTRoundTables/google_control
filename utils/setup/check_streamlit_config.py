#!/usr/bin/env python3
"""
Quick check for Streamlit configuration
"""

import streamlit as st
import os

# Force configuration check
st.title("🔧 Streamlit Configuration Check")

# Display current working directory
st.write(f"**Current directory:** {os.getcwd()}")

# Check config file
config_path = ".streamlit/config.toml"
if os.path.exists(config_path):
    st.success(f"✅ Config file exists: {config_path}")
    
    with open(config_path, 'r') as f:
        content = f.read()
    
    st.code(content, language='toml')
    
    # Check if maxUploadSize is set
    if "maxUploadSize = 500" in content:
        st.success("✅ Upload limit set to 500MB")
    else:
        st.error("❌ Upload limit not properly configured")
        
else:
    st.error(f"❌ Config file missing: {config_path}")

# Test file uploader
st.subheader("📁 File Upload Test")
uploaded_file = st.file_uploader("Test upload", type=['csv'])

if uploaded_file:
    size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    st.success(f"✅ Uploaded: {uploaded_file.name} ({size_mb:.1f} MB)")
    
    if size_mb > 200:
        st.balloons()
        st.success("🎉 Large file upload working!")