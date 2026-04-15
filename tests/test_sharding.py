from lifluct.orchestration.shard import shard_entries


def test_shard_split_is_deterministic_and_complete() -> None:
    entries = list(range(11))
    shards_first = [shard_entries(entries, shard_index=index, shard_count=3) for index in range(3)]
    shards_second = [shard_entries(entries, shard_index=index, shard_count=3) for index in range(3)]

    assert shards_first == shards_second
    flattened = [item for shard in shards_first for item in shard]
    assert sorted(flattened) == entries
    assert len(flattened) == len(set(flattened))
