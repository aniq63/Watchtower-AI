from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="watchtower-sdk",
    version="0.1.1",
    description="Python SDK for Watchtower AI - Data Drift & Quality Monitoring",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Watchtower AI",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
        "pandas>=1.0.0",
        "numpy>=1.19.0"
    ],
    python_requires=">=3.8",
)
