import pytest

from codecov.groups import compute_contiguous_groups


@pytest.mark.parametrize(
    'values, separators, joiners, max_gap, expected',
    [
        # empty input returns no groups
        ([], set(), set(), 3, []),
        # single value forms a one-line group
        ([5], set(), set(), 3, [(5, 5)]),
        # consecutive values are grouped in pass 1
        ([10, 11, 12], set(), set(), 3, [(10, 12)]),
        # gap larger than max_gap without joiners does not merge
        ([1, 2, 7, 8], set(), set(), 3, [(1, 2), (7, 8)]),
        # gap lines that are all joiners are bridged and groups merge
        ([5, 6, 10, 11], set(), {7, 8, 9}, 3, [(5, 11)]),
        # multiple single-line groups merge across joiner-only gaps
        ([1, 3, 5], set(), {2, 4}, 3, [(1, 5)]),
        # chained merges across several joiner-only gaps
        ([1, 2, 5, 6, 10], set(), {3, 4, 7, 8, 9}, 3, [(1, 10)]),
        # gap exactly at max_gap merges when there are no separators
        ([1, 5], set(), set(), 3, [(1, 5)]),
        # gap one line over max_gap does not merge
        ([1, 6], set(), set(), 3, [(1, 1), (6, 6)]),
        # separator line in the gap blocks merging
        ([10, 11, 12, 15, 16], {13}, {14}, 3, [(10, 12), (15, 16)]),
        # large meaningful gap (covered lines) exceeds max_gap and does not merge
        (
            [5, 6, 20, 21],
            {10, 11, 12, 13, 14, 15},
            {7, 8, 9, 16, 17, 18, 19},
            3,
            [(5, 6), (20, 21)],
        ),
    ],
)
def test_compute_contiguous_groups(values, separators, joiners, max_gap, expected):
    """
    values: sorted line numbers to group (e.g. missing coverage lines)
    separators: lines that block merging (e.g. covered or excluded lines)
    joiners: lines that do not count toward gap size (e.g. blanks, comments)
    max_gap: maximum number of non-joiner lines allowed in a gap when merging
    expected: resulting list of (start, end) inclusive ranges
    """
    assert compute_contiguous_groups(values, separators, joiners, max_gap) == expected
