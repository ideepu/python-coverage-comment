import pathlib

from codecov import diff_grouper, groups


def test_get_diff_missing_groups(coverage_obj, diff_coverage_obj):
    result = diff_grouper.get_diff_missing_groups(coverage=coverage_obj, diff_coverage=diff_coverage_obj)

    assert list(result) == [
        groups.Group(file=pathlib.Path('codebase/code.py'), line_start=6, line_end=8),
    ]


def test_get_diff_missing_groups_more_files(coverage_obj_more_files, diff_coverage_obj_more_files):
    result = diff_grouper.get_diff_missing_groups(
        coverage=coverage_obj_more_files,
        diff_coverage=diff_coverage_obj_more_files,
    )

    assert list(result) == [
        groups.Group(file=pathlib.Path('codebase/code.py'), line_start=6, line_end=8),
        groups.Group(file=pathlib.Path('codebase/other.py'), line_start=2, line_end=2),
        groups.Group(file=pathlib.Path('codebase/other.py'), line_start=6, line_end=7),
    ]


def test_get_missing_groups(coverage_obj):
    result = diff_grouper.get_missing_groups(coverage=coverage_obj)

    assert list(result) == [
        groups.Group(file=pathlib.Path('codebase/code.py'), line_start=6, line_end=11),
    ]


def test_get_missing_groups_more_files(coverage_obj_more_files):
    result = diff_grouper.get_missing_groups(coverage=coverage_obj_more_files)

    assert list(result) == [
        groups.Group(file=pathlib.Path('codebase/code.py'), line_start=6, line_end=11),
        groups.Group(file=pathlib.Path('codebase/other.py'), line_start=2, line_end=2),
        groups.Group(file=pathlib.Path('codebase/other.py'), line_start=6, line_end=9),
    ]


def test_get_missing_groups_ignores_branches(coverage_obj):
    """Branches are arcs, not line ranges, so grouping never touches them."""
    list(diff_grouper.get_missing_groups(coverage=coverage_obj))

    assert coverage_obj.files[pathlib.Path('codebase/code.py')].missing_branches == [[5, -5], [10, 11]]
