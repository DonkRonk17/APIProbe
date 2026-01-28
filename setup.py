#!/usr/bin/env python3
"""
Setup script for APIProbe.

Install with:
    pip install -e .

Then use:
    apiprobe --help
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="apiprobe",
    version="1.0.0",
    author="Logan Smith / Metaphy LLC",
    author_email="support@metaphy.io",
    description="API Configuration Validator - Catch misconfigurations before deployment disasters",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/DonkRonk17/APIProbe",
    project_urls={
        "Bug Tracker": "https://github.com/DonkRonk17/APIProbe/issues",
        "Documentation": "https://github.com/DonkRonk17/APIProbe#readme",
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    keywords="api, validation, configuration, testing, ai, gemini, claude, openai, grok",
    py_modules=["apiprobe"],
    python_requires=">=3.7",
    install_requires=[],  # Zero dependencies!
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "apiprobe=apiprobe:main",
        ],
    },
)
