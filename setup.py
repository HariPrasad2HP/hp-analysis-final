#!/usr/bin/env python3
"""
Setup script for GST Analysis System
"""

from setuptools import setup, find_packages
import os

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="gst-analysis-system",
    version="1.0.0",
    author="GST Analysis Team",
    #author_email="",
    description="A comprehensive hierarchical GST data analysis solution",
    long_description=long_description,
    long_description_content_type="text/markdown",
    #url="https://github.com/your-org/gst-analysis-system",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Accounting",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.2.0",
            "pytest-cov>=4.0.0",
            "black>=22.10.0",
            "flake8>=5.0.4",
            "mypy>=0.991",
        ],
        "docs": [
            "sphinx>=5.3.0",
            "sphinx-rtd-theme>=1.1.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "gst-analyze=scripts.run_analysis:main",
            "gst-server=scripts.start_server:main",
            "gst-reports=scripts.generate_reports:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.html", "*.css", "*.js"],
    },
    project_urls={
        "Bug Reports": "https://github.com/your-org/gst-analysis-system/issues",
        "Source": "https://github.com/your-org/gst-analysis-system",
        "Documentation": "https://gst-analysis-system.readthedocs.io/",
    },
)
