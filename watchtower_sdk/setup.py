from setuptools import setup, find_packages

setup(
    name="watchtower-sdk",
    version="0.1.0",
    description="Python SDK for Watchtower AI - Data Drift & Quality Monitoring",
    author="Watchtower AI",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
        "pandas>=1.0.0",
        "numpy>=1.19.0"
    ],
    python_requires=">=3.8",
)
