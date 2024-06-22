# -*- coding: utf-8 -*-
from __future__ import annotations

import pathlib

from codecov import diff_grouper, groups


def test_group_annotations(coverage_obj, diff_coverage_obj):
    result = diff_grouper.get_diff_missing_groups(coverage=coverage_obj, diff_coverage=diff_coverage_obj)

    assert list(result) == [
        groups.Group(file=pathlib.Path('codebase/code.py'), line_start=6, line_end=8),
    ]


def test_group_annotations_more_files(coverage_obj_more_files, diff_coverage_obj_more_files):
    result = diff_grouper.get_diff_missing_groups(
        coverage=coverage_obj_more_files,
        diff_coverage=diff_coverage_obj_more_files,
    )

    assert list(result) == [
        groups.Group(file=pathlib.Path('codebase/code.py'), line_start=5, line_end=8),
        groups.Group(file=pathlib.Path('codebase/other.py'), line_start=1, line_end=1),
        groups.Group(file=pathlib.Path('codebase/other.py'), line_start=5, line_end=8),
    ]


def test_coverage_group_annotations(coverage_obj):
    result = diff_grouper.get_missing_groups(coverage=coverage_obj)

    assert list(result) == [
        groups.Group(file=pathlib.Path('codebase/code.py'), line_start=6, line_end=11),
    ]


def test_coverage_group_annotations_more_files(coverage_obj_more_files):
    result = diff_grouper.get_missing_groups(coverage=coverage_obj_more_files)

    assert list(result) == [
        groups.Group(file=pathlib.Path('codebase/code.py'), line_start=5, line_end=8),
        groups.Group(file=pathlib.Path('codebase/other.py'), line_start=1, line_end=1),
        groups.Group(file=pathlib.Path('codebase/other.py'), line_start=5, line_end=8),
    ]


def test_flatten_branches():
    assert not diff_grouper.flatten_branches(branches=None)

    flattened_branches = diff_grouper.flatten_branches([[1, 2], [3, 4]])
    assert flattened_branches == [1, 2, 3, 4]

    flattened_branches = diff_grouper.flatten_branches([[1, 1]])
    assert flattened_branches == [1]

    flattened_branches = diff_grouper.flatten_branches([[-1, -2], [3, 4]])
    assert flattened_branches == [1, 2, 3, 4]

    flattened_branches = diff_grouper.flatten_branches([[-1, -2], [3, 4], [5, 5]])
    assert flattened_branches == [1, 2, 3, 4, 5]


def test_group_branch_annotations(coverage_obj, diff_coverage_obj):
    result = diff_grouper.get_branch_missing_groups(coverage=coverage_obj, diff_coverage=diff_coverage_obj)

    assert list(result) == [
        groups.Group(file=pathlib.Path('codebase/code.py'), line_start=5, line_end=6),
        groups.Group(file=pathlib.Path('codebase/code.py'), line_start=10, line_end=11),
    ]


def test_group_branch_annotations_more_files(coverage_obj_more_files, diff_coverage_obj_more_files):
    result = diff_grouper.get_branch_missing_groups(
        coverage=coverage_obj_more_files,
        diff_coverage=diff_coverage_obj_more_files,
    )

    assert list(result) == [
        groups.Group(file=pathlib.Path('codebase/code.py'), line_start=4, line_end=5),
        groups.Group(file=pathlib.Path('codebase/code.py'), line_start=7, line_end=8),
        groups.Group(file=pathlib.Path('codebase/other.py'), line_start=2, line_end=3),
        groups.Group(file=pathlib.Path('codebase/other.py'), line_start=4, line_end=5),
        groups.Group(file=pathlib.Path('codebase/other.py'), line_start=8, line_end=9),
    ]
