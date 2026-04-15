"""Deterministic manifest sharding helpers."""

from __future__ import annotations

from typing import Sequence, TypeVar

T = TypeVar("T")


def shard_entries(entries: Sequence[T], *, shard_index: int, shard_count: int) -> list[T]:
    if shard_count <= 0:
        raise ValueError("shard_count must be positive")
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError("shard_index must be in [0, shard_count)")
    return [entry for index, entry in enumerate(entries) if index % shard_count == shard_index]
