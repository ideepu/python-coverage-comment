import dataclasses
import decimal
import pathlib

from codecov.config import Config, TestFramework
from codecov.coverage.base import BaseCoverageHandler, DiffCoverage, FileDiffCoverage


@dataclasses.dataclass
class JestCoverageInfo:  # pylint: disable=too-many-instance-attributes
    num_statements: int
    covered_lines: int
    missing_lines: int
    excluded_lines: int
    num_functions: int
    covered_functions: int
    missing_functions: int
    percent_covered: decimal.Decimal
    percent_covered_display: str


@dataclasses.dataclass
class JestFileCoverage:
    path: pathlib.Path
    covered_lines: list[int]
    missing_lines: list[int]
    excluded_lines: list[int]
    info: JestCoverageInfo


@dataclasses.dataclass
class JestCoverage:
    info: JestCoverageInfo
    files: dict[pathlib.Path, JestFileCoverage]


class JestCoverageHandler(BaseCoverageHandler):
    TEST_FRAMEWORK: TestFramework = TestFramework.JEST

    """
    {
        "/app/sample/index.ts": {
            "path": "/app/sample/index.ts",
            "statementMap": {},
            "fnMap": {},
            "branchMap": {},
            "s": {},
            "f": {},
            "b": {},
            "_coverageSchema": "1a1c01bbd47fc00a2c39e90264f33305004495a9",
            "hash": "8d4713275a40f0982d031526eae55ee00e551b73"
        },
    }
    """

    def compute_coverage(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        num_covered: int,
        num_total: int,
        num_functions_covered: int = 0,
        num_functions_total: int = 0,
        num_branches_covered: int = 0,
        num_branches_total: int = 0,
    ) -> decimal.Decimal:
        numerator = decimal.Decimal(num_covered + num_branches_covered + num_functions_covered)
        denominator = decimal.Decimal(num_total + num_branches_total + num_functions_total)
        if denominator == 0:
            return decimal.Decimal('1')
        return numerator / denominator

    # TODO: use pct helper
    def _get_percentage_display(self, value: decimal.Decimal) -> str:
        percentage_display = str(self.convert_to_decimal(value=value) * 100)
        return percentage_display.split('.', maxsplit=1)[0]

    def _get_function_map_coverage(self, file_data: dict) -> dict[str, set[int]]:
        covered_lines: set[int] = set()
        missing_lines: set[int] = set()
        for line, count in file_data['f'].items():
            if count > 0:
                start = file_data['fnMap'][line]['loc']['start']['line']
                end = file_data['fnMap'][line]['loc']['end']['line']
                covered_lines.update(range(start, end + 1))
            else:
                start = file_data['fnMap'][line]['loc']['start']['line']
                end = file_data['fnMap'][line]['loc']['end']['line']
                missing_lines.update(range(start, end + 1))
        return {
            'covered_lines': covered_lines,
            'missing_lines': missing_lines,
        }

    def _get_statement_map_coverage(self, file_data: dict) -> dict[str, set[int]]:
        covered_lines: set[int] = set()
        missing_lines: set[int] = set()
        for line, count in file_data['s'].items():
            if count > 0:
                start = file_data['statementMap'][line]['start']['line']
                end = file_data['statementMap'][line]['end']['line']
                covered_lines.update(range(start, end + 1))
            else:
                start = file_data['statementMap'][line]['start']['line']
                end = file_data['statementMap'][line]['end']['line']
                missing_lines.update(range(start, end + 1))

        return {
            'covered_lines': covered_lines,
            'missing_lines': missing_lines,
        }

    def extract_file_coverage(self, file_data: dict) -> JestFileCoverage:
        statement_map_coverage = self._get_statement_map_coverage(file_data)
        function_map_coverage = self._get_function_map_coverage(file_data)
        total_covered_lines = statement_map_coverage['covered_lines'] | function_map_coverage['covered_lines']
        total_missing_lines = statement_map_coverage['missing_lines'] | function_map_coverage['missing_lines']

        # Partially covered lines can be in both covered and missing lines
        # Remove missing lines from covered since they are not fully covered
        total_covered_lines -= total_missing_lines

        num_covered_lines = len(total_covered_lines)
        num_missing_lines = len(total_missing_lines)
        num_statements = len(total_covered_lines) + len(total_missing_lines)

        percent_covered = self.compute_coverage(num_covered=num_covered_lines, num_total=num_statements)
        return JestFileCoverage(
            path=pathlib.Path(file_data['path']),
            excluded_lines=[],  # TODO: Add excluded lines
            missing_lines=list(total_missing_lines),
            covered_lines=list(total_covered_lines),
            info=JestCoverageInfo(
                covered_lines=num_covered_lines,
                num_statements=num_statements,
                missing_lines=num_missing_lines,
                excluded_lines=0,  # TODO: Add excluded lines
                num_functions=0,
                covered_functions=0,
                missing_functions=0,
                percent_covered=percent_covered,
                percent_covered_display=self._get_percentage_display(value=percent_covered),
            ),
        )

    def extract_info(self, data: dict) -> JestCoverage:
        files: dict[pathlib.Path, JestFileCoverage] = {}
        total_covered_lines: int = 0
        total_num_statements: int = 0
        total_missing_lines: int = 0
        total_excluded_lines: int = 0
        for file_data in data.values():
            file_coverage = self.extract_file_coverage(file_data)
            files[pathlib.Path(file_data['path'])] = file_coverage
            total_covered_lines += file_coverage.info.covered_lines
            total_num_statements += file_coverage.info.num_statements
            total_missing_lines += file_coverage.info.missing_lines
            total_excluded_lines += file_coverage.info.excluded_lines

        percent_covered = self.compute_coverage(num_covered=total_covered_lines, num_total=total_num_statements)
        return JestCoverage(
            files=files,
            info=JestCoverageInfo(
                covered_lines=total_covered_lines,
                num_statements=total_num_statements,
                missing_lines=total_missing_lines,
                excluded_lines=total_excluded_lines,
                num_functions=0,
                covered_functions=0,
                missing_functions=0,
                percent_covered=percent_covered,
                percent_covered_display=self._get_percentage_display(value=percent_covered),
            ),
        )

    def get_file_diff_coverage(self, file: JestFileCoverage, added_lines: list[int]) -> FileDiffCoverage:
        covered = set(file.covered_lines) & set(added_lines)
        missing = set(file.missing_lines) & set(added_lines)
        # Added lines includes comments, blank lines, etc in the diff, So we take the actual statements in the file
        added = covered | missing
        return FileDiffCoverage(
            path=file.path,
            percent_covered=self.compute_coverage(num_covered=len(covered), num_total=len(added)),
            covered_statements=sorted(covered),
            missing_statements=sorted(missing),
            added_statements=sorted(added),
            added_lines=added_lines,
        )

    def get_diff_coverage(  # pylint: disable=duplicate-code
        self,
        added_lines: dict[pathlib.Path, list[int]],
        coverage: JestCoverage,
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

            file_diff_coverage = self.get_file_diff_coverage(file=file, added_lines=added_lines_for_file)
            files[path] = file_diff_coverage
            total_num_lines += len(file_diff_coverage.added_statements)
            total_num_violations += len(file_diff_coverage.missing_statements)

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
