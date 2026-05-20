"""
TMDB-клиент для runtime API (переиспользует scripts.tmdb_client).
"""
from scripts.tmdb_client import TMDB_IMAGE_BASE, TmdbClient

__all__ = ["TmdbClient", "TMDB_IMAGE_BASE"]
