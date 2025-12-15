"""Collector Gateway service package."""

from .bootstrap import build_adapters
from .service import CollectorService

__all__ = ["CollectorService", "build_adapters"]
