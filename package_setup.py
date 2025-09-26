#!/usr/bin/env python3
"""
Setup script for Maps Link Monitoring Application
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="maps-link-monitoring",
    version="1.0.0",
    author="Maps Link Monitoring Team",
    description="A comprehensive monitoring and analysis system for Google Directions API links",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(where="."),
    package_dir={"": "."},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "maps-monitor=app:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.csv", "*.md", "*.txt"],
    },
)