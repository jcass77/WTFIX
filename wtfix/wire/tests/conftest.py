import pytest

from ...protocol import utils


@pytest.fixture(scope="session")
def routing_id_group_pairs(routing_id_group):
    """Returns a list of (tag, value) tuples for the repeating group"""
    group = routing_id_group
    pairs = [(utils.fix_tag(routing_id_group.tag), routing_id_group.value)]
    for instance in group:
        pairs += [(utils.fix_tag(tag), value) for tag, value in instance.fields]

    return pairs
