#!/usr/bin/env python3
"""
Simple test to verify upload limit configuration
"""

import streamlit as st
import os

st.title("🔧 Upload Limit Test")

# Show current configuration
st.subheader("📋 Configuration Status")

config_path = ".streamlit/config.toml"
if os.path.exists(config_path):
    st.success("✅ Configuration file found")
    
    with open(config_path, 'r') as f:
        config_content = f.read()
    
    st.code(config_content, language='toml')
    
    # Check for the upload size setting
    if "maxUploadSize = 500" in config_content:
        st.success("✅ Upload limit set to 500MB in config")
    else:
        st.error("❌ Upload limit not found in config")
else:
    st.error("❌ Configuration file not found")

# Test file uploader
st.subheader("📁 File Upload Test")
st.info("Try uploading your data.csv file (267MB)")

uploaded_file = st.file_uploader(
    "Test large file upload",
    type=['csv'],
    help="This should accept files up to 500MB"
)

if uploaded_file is not None:
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    st.success(f"🎉 SUCCESS! File uploaded: {uploaded_file.name}")
    st.write(f"**File size:** {file_size_mb:.1f} MB")
    
    if file_size_mb > 200:
        st.balloons()
        st.success("✅ Large file upload is working! The 500MB limit is active!")
    
    # Show first few lines
    st.subheader("📄 File Preview")
    try:
        content = uploaded_file.getvalue().decode('utf-8')
        lines = content.split('\n')[:5]
        for i, line in enumerate(lines):
            st.text(f"Line {i+1}: {line[:100]}...")
    except Exception as e:
        st.error(f"Error reading file: {e}")

st.subheader("🔍 Debug Info")
st.write(f"**Current working directory:** {os.getcwd()}")
st.write(f"**Config file exists:** {os.path.exists(config_path)}")

# Show environment info
import streamlit as st
st.write(f"**Streamlit version:** {st.__version__}")