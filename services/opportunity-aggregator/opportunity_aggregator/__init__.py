"""Opportunity aggregator service package."""

from .config import AggregatorSettings, get_settings
from .service import OpportunityAggregatorService

__all__ = ["AggregatorSettings", "get_settings", "OpportunityAggregatorService"]
