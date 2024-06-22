# -*- coding: utf-8 -*-
from __future__ import annotations

from collections.abc import Iterable

from codecov import coverage as coverage_module, groups

MAX_ANNOTATION_GAP = 3


def get_missing_groups(
    coverage: coverage_module.Coverage,
) -> Iterable[groups.Group]:
    for path, coverage_file in coverage.files.items():
        # Lines that are covered or excluded should not be considered for
        # filling a gap between violation groups.
        # (so, lines that can appear in a gap are lines that are missing, or
        # lines that do not contain code: blank lines or lines containing comments)
        separators = {
            *coverage_file.executed_lines,
            *coverage_file.excluded_lines,
        }
        # Lines that should be considered for filling a gap, unless
        # they are separators.
        joiners = set(range(1, coverage_file.info.num_statements)) - separators

        for start, end in groups.compute_contiguous_groups(
            values=coverage_file.missing_lines,
            separators=separators,
            joiners=joiners,
            max_gap=MAX_ANNOTATION_GAP,
        ):
            yield groups.Group(
                file=path,
                line_start=start,
                line_end=end,
            )


def flatten_branches(branches: list[list[int]] | None) -> list[int]:
    flattened_branches: list[int] = []
    if not branches:
        return flattened_branches

    for branch in branches:
        start, end = abs(branch[0]), abs(branch[1])
        if start == end:
            flattened_branches.append(start)
        else:
            flattened_branches.extend(range(min(start, end), max(start, end) + 1))
    return flattened_branches


def get_branch_missing_groups(
    coverage: coverage_module.Coverage,
    diff_coverage: coverage_module.DiffCoverage,
) -> Iterable[groups.Group]:
    for path, _ in diff_coverage.files.items():
        coverage_file = coverage.files[path]
        for start, end in coverage_file.missing_branches or []:
            yield groups.Group(
                file=path,
                line_start=start,
                line_end=end,
            )


def group_branches(coverage: coverage_module.Coverage) -> coverage_module.Coverage:
    for file_coverage in coverage.files.values():
        separators = {
            *flatten_branches(file_coverage.executed_branches),
            *file_coverage.excluded_lines,
        }
        joiners = set(range(1, file_coverage.info.num_statements)) - separators

        file_coverage.missing_branches = [
            [start, end]
            for start, end in groups.compute_contiguous_groups(
                values=flatten_branches(branches=file_coverage.missing_branches),
                separators=separators,
                joiners=joiners,
                max_gap=MAX_ANNOTATION_GAP,
            )
        ]
    return coverage


def get_diff_missing_groups(
    coverage: coverage_module.Coverage,
    diff_coverage: coverage_module.DiffCoverage,
) -> Iterable[groups.Group]:
    for path, diff_file in diff_coverage.files.items():
        coverage_file = coverage.files[path]
        separators = {
            *coverage_file.executed_lines,
            *coverage_file.excluded_lines,
        }
        joiners = set(diff_file.added_lines) - separators

        for start, end in groups.compute_contiguous_groups(
            values=diff_file.missing_statements,
            separators=separators,
            joiners=joiners,
            max_gap=MAX_ANNOTATION_GAP,
        ):
            yield groups.Group(
                file=path,
                line_start=start,
                line_end=end,
            )
