import dataclasses
import datetime
import decimal
import pathlib

from codecov import diff_grouper
from codecov.config import Config, TestFramework
from codecov.coverage.base import BaseCoverage, BaseCoverageHandler, DiffCoverage, FileDiffCoverage


@dataclasses.dataclass
class PytestCoverageInfo:  # pylint: disable=too-many-instance-attributes
    covered_lines: int
    num_statements: int
    missing_lines: int
    excluded_lines: int
    num_branches: int | None
    num_partial_branches: int | None  # TODO: Removed this
    covered_branches: int | None
    missing_branches: int | None
    percent_covered: decimal.Decimal
    percent_covered_display: str


@dataclasses.dataclass
class PytestFileCoverage:
    path: pathlib.Path
    covered_lines: list[int]
    missing_lines: list[int]
    excluded_lines: list[int]
    info: PytestCoverageInfo
    executed_branches: list[list[int]] | None
    missing_branches: list[list[int]] | None


@dataclasses.dataclass
class PytestCoverageMetadata:
    version: str
    timestamp: datetime.datetime
    branch_coverage: bool
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
        num_branches_covered: int = 0,
        num_branches_total: int = 0,
    ) -> decimal.Decimal:
        numerator = decimal.Decimal(num_covered + num_branches_covered)
        denominator = decimal.Decimal(num_total + num_branches_total)
        if denominator == 0:
            return decimal.Decimal('1')
        return numerator / denominator

    def extract_meta(self, data: dict) -> PytestCoverageMetadata:
        return PytestCoverageMetadata(
            version=data['meta']['version'],
            timestamp=datetime.datetime.fromisoformat(data['meta']['timestamp']),
            branch_coverage=data['meta']['branch_coverage'],
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
            num_branches=data.get('num_branches'),
            num_partial_branches=data.get('num_partial_branches'),
            covered_branches=data.get('covered_branches'),
            missing_branches=data.get('missing_branches'),
        )

    def extract_file_coverage(self, path: str, file_data: dict) -> PytestFileCoverage:
        return PytestFileCoverage(
            path=pathlib.Path(path),
            excluded_lines=file_data['excluded_lines'],
            missing_lines=file_data['missing_lines'],
            covered_lines=file_data['executed_lines'],
            executed_branches=file_data.get('executed_branches'),
            missing_branches=file_data.get('missing_branches'),
            info=self.extract_coverage_info(file_data['summary']),
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
        return PytestCoverage(
            meta=self.extract_meta(data),
            files={
                pathlib.Path(path): self.extract_file_coverage(path, file_data)
                for path, file_data in data['files'].items()
            },
            info=self.extract_coverage_info(data['totals']),
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
        total_num_branches_covered = 0
        total_num_branches = 0
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

            if config.BRANCH_COVERAGE:
                total_num_branches_covered += file.info.covered_branches or 0
                total_num_branches += file.info.num_branches or 0
                percent_covered = self.compute_coverage(
                    num_covered=count_executed,
                    num_total=count_total,
                    num_branches_covered=file.info.covered_branches or 0,
                    num_branches_total=file.info.num_branches or 0,
                )
            else:
                percent_covered = self.compute_coverage(num_covered=count_executed, num_total=count_total)

            files[path] = FileDiffCoverage(
                path=path,
                percent_covered=percent_covered,
                covered_statements=sorted(executed),
                missing_statements=sorted(missing),
                added_statements=sorted(added),
                added_lines=added_lines_for_file,
            )
        if config.BRANCH_COVERAGE:
            final_percentage = self.compute_coverage(
                num_covered=total_num_lines - total_num_violations,
                num_total=total_num_lines,
                num_branches_covered=total_num_branches_covered,
                num_branches_total=total_num_branches,
            )
        else:
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

    def get_coverage(self, config: Config) -> PytestCoverage:
        coverage = super().get_coverage(config=config)

        if config.BRANCH_COVERAGE:
            coverage = diff_grouper.fill_branch_missing_groups(coverage=coverage)

        return coverage
