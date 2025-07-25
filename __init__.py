"""
GeoDataReader Package

A Python toolbox to download and read geotechnical data including CPTs from various sources.
"""

__version__ = "1.1"
__author__ = "Eleni Smyrniou, Bruno Zuada Coelho"

# Import main functionality for easy access
from BroReader.read_BRO import read_cpts

__all__ = ['read_cpts']
