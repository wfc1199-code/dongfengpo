"""Data models shared by the cleaner service."""

from data_contracts import CleanedTick, TickRecord

RawTick = TickRecord
CleanTick = CleanedTick

__all__ = ["RawTick", "CleanTick"]
