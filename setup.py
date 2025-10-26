#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Setup script for EkahauBOM package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text(encoding="utf-8").splitlines()
    requirements = [r.strip() for r in requirements if r.strip() and not r.startswith("#")]

setup(
    name="ekahau-bom",
    version="2.5.0",
    author="Pavel Semenischev",
    author_email="",
    description="Bill of Materials (BOM) generator for Ekahau AI project files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/htechno/EkahauBOM",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Telecommunications Industry",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "ekahau-bom=ekahau_bom.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "ekahau_bom": ["py.typed"],
    },
    zip_safe=False,
    keywords="ekahau bom bill-of-materials wireless wifi networking",
)
