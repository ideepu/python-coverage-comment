# -*- coding: utf-8 -*-
from __future__ import annotations

import dataclasses
import datetime
import decimal
import json
import pathlib
from collections import deque
from collections.abc import Sequence

from codecov import log


@dataclasses.dataclass
class CoverageMetadata:
    version: str
    timestamp: datetime.datetime
    branch_coverage: bool
    show_contexts: bool


@dataclasses.dataclass
class CoverageInfo:  # pylint: disable=too-many-instance-attributes
    covered_lines: int
    num_statements: int
    percent_covered: decimal.Decimal
    percent_covered_display: str
    missing_lines: int
    excluded_lines: int
    num_branches: int | None
    num_partial_branches: int | None
    covered_branches: int | None
    missing_branches: int | None


@dataclasses.dataclass
class FileCoverage:
    path: pathlib.Path
    executed_lines: list[int]
    missing_lines: list[int]
    excluded_lines: list[int]
    executed_branches: list[list[int]] | None
    missing_branches: list[list[int]] | None
    info: CoverageInfo


@dataclasses.dataclass
class Coverage:
    meta: CoverageMetadata
    info: CoverageInfo
    files: dict[pathlib.Path, FileCoverage]


@dataclasses.dataclass
class FileDiffCoverage:
    path: pathlib.Path
    percent_covered: decimal.Decimal
    covered_statements: list[int]
    missing_statements: list[int]
    added_statements: list[int]
    # Added lines tracks all the lines that were added in the diff, not just
    # the statements (so it includes comments, blank lines, etc.)
    added_lines: list[int]

    # for backward compatibility
    @property
    def violation_lines(self) -> list[int]:
        return self.missing_statements


@dataclasses.dataclass
class DiffCoverage:
    total_num_lines: int
    total_num_violations: int
    total_percent_covered: decimal.Decimal
    num_changed_lines: int
    files: dict[pathlib.Path, FileDiffCoverage]


def compute_coverage(num_covered: int, num_total: int) -> decimal.Decimal:
    if num_total == 0:
        return decimal.Decimal('1')
    return decimal.Decimal(num_covered) / decimal.Decimal(num_total)


def get_coverage_info(coverage_path: pathlib.Path) -> Coverage:
    try:
        with coverage_path.open() as coverage_data:
            json_coverage = json.loads(coverage_data.read())
    except FileNotFoundError:
        log.error('Coverage report file not found: %s', coverage_path)
        raise
    except json.JSONDecodeError:
        log.error('Invalid JSON format in coverage report file: %s', coverage_path)
        raise

    return extract_info(data=json_coverage)


def extract_info(data: dict) -> Coverage:
    """
    {
        "meta": {
            "version": "5.5",
            "timestamp": "2021-12-26T22:27:40.683570",
            "branch_coverage": True,
            "show_contexts": False,
        },
        "files": {
            "codebase/code.py": {
                "executed_lines": [1, 2, 5, 6, 9],
                "summary": {
                    "covered_lines": 42,
                    "num_statements": 46,
                    "percent_covered": 88.23529411764706,
                    "percent_covered_display": "88",
                    "missing_lines": 4,
                    "excluded_lines": 0,
                    "num_branches": 22,
                    "num_partial_branches": 4,
                    "covered_branches": 18,
                    "missing_branches": 4
                },
                "missing_lines": [7],
                "excluded_lines": [],
                "executed_branches": [],
                "missing_branches": [],
            }
        },
        "totals": {
            "covered_lines": 5,
            "num_statements": 6,
            "percent_covered": 75.0,
            "percent_covered_display": "75",
            "missing_lines": 1,
            "excluded_lines": 0,
            "num_branches": 2,
            "num_partial_branches": 1,
            "covered_branches": 1,
            "missing_branches": 1,
        },
    }
    """
    return Coverage(
        meta=CoverageMetadata(
            version=data['meta']['version'],
            timestamp=datetime.datetime.fromisoformat(data['meta']['timestamp']),
            branch_coverage=data['meta']['branch_coverage'],
            show_contexts=data['meta']['show_contexts'],
        ),
        files={
            pathlib.Path(path): FileCoverage(
                path=pathlib.Path(path),
                excluded_lines=file_data['excluded_lines'],
                missing_lines=file_data['missing_lines'],
                executed_lines=file_data['executed_lines'],
                executed_branches=file_data.get('executed_branches'),
                missing_branches=file_data.get('missing_branches'),
                info=CoverageInfo(
                    covered_lines=file_data['summary']['covered_lines'],
                    num_statements=file_data['summary']['num_statements'],
                    percent_covered=file_data['summary']['percent_covered'],
                    percent_covered_display=file_data['summary']['percent_covered_display'],
                    missing_lines=file_data['summary']['missing_lines'],
                    excluded_lines=file_data['summary']['excluded_lines'],
                    num_branches=file_data['summary'].get('num_branches'),
                    num_partial_branches=file_data['summary'].get('num_partial_branches'),
                    covered_branches=file_data['summary'].get('covered_branches'),
                    missing_branches=file_data['summary'].get('missing_branches'),
                ),
            )
            for path, file_data in data['files'].items()
        },
        info=CoverageInfo(
            covered_lines=data['totals']['covered_lines'],
            num_statements=data['totals']['num_statements'],
            percent_covered=data['totals']['percent_covered'],
            percent_covered_display=data['totals']['percent_covered_display'],
            missing_lines=data['totals']['missing_lines'],
            excluded_lines=data['totals']['excluded_lines'],
            num_branches=data['totals'].get('num_branches'),
            num_partial_branches=data['totals'].get('num_partial_branches'),
            covered_branches=data['totals'].get('covered_branches'),
            missing_branches=data['totals'].get('missing_branches'),
        ),
    )


# pylint: disable=too-many-locals
def get_diff_coverage_info(added_lines: dict[pathlib.Path, list[int]], coverage: Coverage) -> DiffCoverage:
    files = {}
    total_num_lines = 0
    total_num_violations = 0
    num_changed_lines = 0

    for path, added_lines_for_file in added_lines.items():
        num_changed_lines += len(added_lines_for_file)

        try:
            file = coverage.files[path]
        except KeyError:
            continue

        executed = set(file.executed_lines) & set(added_lines_for_file)
        count_executed = len(executed)

        missing = set(file.missing_lines) & set(added_lines_for_file)
        count_missing = len(missing)

        added = executed | missing
        count_total = len(added)

        total_num_lines += count_total
        total_num_violations += count_missing

        percent_covered = compute_coverage(num_covered=count_executed, num_total=count_total)

        files[path] = FileDiffCoverage(
            path=path,
            percent_covered=percent_covered,
            covered_statements=sorted(executed),
            missing_statements=sorted(missing),
            added_statements=sorted(added),
            added_lines=added_lines_for_file,
        )
    final_percentage = compute_coverage(
        num_covered=total_num_lines - total_num_violations,
        num_total=total_num_lines,
    )

    return DiffCoverage(
        total_num_lines=total_num_lines,
        total_num_violations=total_num_violations,
        total_percent_covered=final_percentage,
        num_changed_lines=num_changed_lines,
        files=files,
    )


def parse_diff_output(diff: str) -> dict[pathlib.Path, list[int]]:
    current_file: pathlib.Path | None = None
    added_filename_prefix = '+++ b/'
    result: dict[pathlib.Path, list[int]] = {}
    diff_lines: deque[str] = deque()
    diff_lines.extend(diff.splitlines())
    while diff_lines:
        line = diff_lines.popleft()
        if line.startswith(added_filename_prefix):
            current_file = pathlib.Path(line.removeprefix(added_filename_prefix))
            continue
        if line.startswith('@@'):

            def parse_line_number_diff_line(diff_line: str) -> Sequence[int]:
                """
                Parse the "added" part of the line number diff text:
                    @@ -60,0 +61 @@ def compute_files(  -> [64]
                    @@ -60,0 +61,9 @@ def compute_files(  -> [64, 65, 66]

                Github API returns default context lines 3 at start and end, we need to remove them.
                """
                start, _ = (int(i) for i in (diff_line.split()[2][1:] + ',1').split(',')[:2])

                line_start = line_end = start
                while diff_lines:
                    next_line = diff_lines.popleft()
                    if next_line.startswith(' '):
                        line_start += 1
                        line_end += 1
                        continue

                    if next_line.startswith('-'):
                        continue

                    diff_lines.appendleft(next_line)
                    break

                last_added_line = line_end
                while diff_lines:
                    next_line = diff_lines.popleft()
                    if next_line.startswith(' ') or next_line.startswith('+'):
                        line_end += 1
                        if next_line.startswith('+'):
                            last_added_line = line_end
                        continue

                    if next_line.startswith('-'):
                        continue

                    diff_lines.appendleft(next_line)
                    break

                return range(line_start, last_added_line)

            lines = parse_line_number_diff_line(diff_line=line)
            if len(lines) > 0:
                if current_file is None:
                    raise ValueError(f'Unexpected diff output format: \n{diff}')
                result.setdefault(current_file, []).extend(lines)

    return result
