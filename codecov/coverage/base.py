from __future__ import annotations

import dataclasses
import datetime
import decimal
import json
import pathlib
from abc import ABC, abstractmethod

from codecov.exceptions import ConfigurationException
from codecov.log import log


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


@dataclasses.dataclass
class DiffCoverage:
    total_num_lines: int
    total_num_violations: int
    total_percent_covered: decimal.Decimal
    num_changed_lines: int
    files: dict[pathlib.Path, FileDiffCoverage]


class BaseCoverage(ABC):
    def compute_coverage(self, num_covered: int, num_total: int) -> decimal.Decimal:
        if num_total == 0:
            return decimal.Decimal('1')
        return decimal.Decimal(num_covered) / decimal.Decimal(num_total)

    def get_coverage_info(self, coverage_path: pathlib.Path) -> Coverage:
        try:
            with coverage_path.open() as coverage_data:
                json_coverage = json.loads(coverage_data.read())
        except FileNotFoundError as exc:
            log.error('Coverage report file not found at the specified location: %s', coverage_path)
            raise ConfigurationException from exc
        except json.JSONDecodeError as exc:
            log.error('Invalid JSON format in coverage report file: %s', coverage_path)
            raise ConfigurationException from exc

        return self.extract_info(data=json_coverage)

    @abstractmethod
    def extract_info(self, data: dict) -> Coverage:
        raise NotImplementedError  # pragma: no cover

    def get_diff_coverage_info(  # pylint: disable=too-many-locals
        self,
        added_lines: dict[pathlib.Path, list[int]],
        coverage: Coverage,
    ) -> DiffCoverage:
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

            percent_covered = self.compute_coverage(num_covered=count_executed, num_total=count_total)

            files[path] = FileDiffCoverage(
                path=path,
                percent_covered=percent_covered,
                covered_statements=sorted(executed),
                missing_statements=sorted(missing),
                added_statements=sorted(added),
                added_lines=added_lines_for_file,
            )
        final_percentage = self.compute_coverage(
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
