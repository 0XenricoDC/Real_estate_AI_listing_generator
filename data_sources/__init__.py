"""
Data Sources - Gestione unificata di API e Scrapers
"""

from .base import BaseDataSource
from .factory import get_data_source, get_all_data_sources

__all__ = ['BaseDataSource', 'get_data_source', 'get_all_data_sources']
