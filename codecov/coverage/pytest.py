import dataclasses
import datetime
import decimal
import pathlib

from codecov.config import Config, TestFramework
from codecov.coverage.base import BaseCoverage, BaseCoverageHandler, DiffCoverage, FileDiffCoverage


def _branch_missing_lines(missing_branches: list[list[int]] | None) -> list[int]:
    if not missing_branches:
        return []

    lines: list[int] = []
    for branch in missing_branches:
        from_line = abs(branch[0])
        if from_line > 0:
            lines.append(from_line)
        to_line = abs(branch[1])
        if to_line > 0 and to_line != from_line:
            lines.append(to_line)
    return lines


def _incorporate_branch_missing(
    covered_lines: list[int],
    missing_lines: list[int],
    missing_branches: list[list[int]] | None,
) -> tuple[list[int], list[int]]:
    branch_lines = _branch_missing_lines(missing_branches)
    if not branch_lines:
        return covered_lines, missing_lines

    missing = sorted(set(missing_lines) | set(branch_lines))
    covered = sorted(set(covered_lines) - set(branch_lines))
    return covered, missing


@dataclasses.dataclass
class PytestCoverageInfo:  # pylint: disable=too-many-instance-attributes
    covered_lines: int
    num_statements: int
    missing_lines: int
    excluded_lines: int
    percent_covered: decimal.Decimal
    percent_covered_display: str


@dataclasses.dataclass
class PytestFileCoverage:
    path: pathlib.Path
    covered_lines: list[int]
    missing_lines: list[int]
    excluded_lines: list[int]
    info: PytestCoverageInfo


@dataclasses.dataclass
class PytestCoverageMetadata:
    version: str
    timestamp: datetime.datetime
    show_contexts: bool


@dataclasses.dataclass
class PytestCoverage(BaseCoverage):
    info: PytestCoverageInfo
    files: dict[pathlib.Path, PytestFileCoverage]
    meta: PytestCoverageMetadata


class PytestCoverageHandler(BaseCoverageHandler[PytestCoverage]):
    TEST_FRAMEWORK: TestFramework = TestFramework.PYTEST

    def compute_coverage(
        self,
        num_covered: int,
        num_total: int,
    ) -> decimal.Decimal:
        numerator = decimal.Decimal(num_covered)
        denominator = decimal.Decimal(num_total)
        if denominator == 0:
            return decimal.Decimal('1')
        return numerator / denominator

    def extract_meta(self, data: dict) -> PytestCoverageMetadata:
        return PytestCoverageMetadata(
            version=data['meta']['version'],
            timestamp=datetime.datetime.fromisoformat(data['meta']['timestamp']),
            show_contexts=data['meta']['show_contexts'],
        )

    def extract_coverage_info(self, data: dict) -> PytestCoverageInfo:
        return PytestCoverageInfo(
            covered_lines=data['covered_lines'],
            num_statements=data['num_statements'],
            percent_covered=self.convert_to_decimal(data['percent_covered']),
            percent_covered_display=data['percent_covered_display'],
            missing_lines=data['missing_lines'],
            excluded_lines=data['excluded_lines'],
        )

    def extract_file_coverage(self, path: str, file_data: dict) -> PytestFileCoverage:
        covered_lines, missing_lines = _incorporate_branch_missing(
            covered_lines=file_data['executed_lines'],
            missing_lines=file_data['missing_lines'],
            missing_branches=file_data.get('missing_branches'),
        )
        info = self.extract_coverage_info(file_data['summary'])
        return PytestFileCoverage(
            path=pathlib.Path(path),
            excluded_lines=file_data['excluded_lines'],
            missing_lines=missing_lines,
            covered_lines=covered_lines,
            info=dataclasses.replace(
                info,
                covered_lines=len(covered_lines),
                missing_lines=len(missing_lines),
            ),
        )

    def extract_info(self, data: dict) -> PytestCoverage:
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
                    },
                    "missing_lines": [7],
                    "excluded_lines": [],
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
            },
        }
        """
        files = {
            pathlib.Path(path): self.extract_file_coverage(path, file_data) for path, file_data in data['files'].items()
        }
        total_covered_lines = sum(file.info.covered_lines for file in files.values())
        total_missing_lines = sum(file.info.missing_lines for file in files.values())
        info = self.extract_coverage_info(data['totals'])
        return PytestCoverage(
            meta=self.extract_meta(data),
            files=files,
            info=dataclasses.replace(
                info,
                covered_lines=total_covered_lines,
                missing_lines=total_missing_lines,
            ),
        )

    def get_diff_coverage(  # pylint: disable=too-many-locals
        self,
        added_lines: dict[pathlib.Path, list[int]],
        coverage: PytestCoverage,
        config: Config,
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

            executed = set(file.covered_lines) & set(added_lines_for_file)
            count_executed = len(executed)

            missing = set(file.missing_lines) & set(added_lines_for_file)
            count_missing = len(missing)

            # Added lines includes comments, blank lines, etc in the diff, So we take the actual statements in the file
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
