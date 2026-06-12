import dataclasses
import datetime
import json
import pathlib
from unittest.mock import patch

from codecov.coverage.pytest import (
    PytestCoverage,
    PytestCoverageHandler,
    PytestCoverageInfo,
    PytestCoverageMetadata,
    PytestFileCoverage,
)


class TestPytestCoverage:
    def test_extract_info(self, coverage_json):
        expected_coverage = PytestCoverage(
            meta=PytestCoverageMetadata(
                version='1.2.3',
                timestamp=datetime.datetime.fromisoformat('2000-01-01T00:00:00'),
                branch_coverage=True,
                show_contexts=False,
            ),
            files={
                pathlib.Path('codebase/code.py'): PytestFileCoverage(
                    path=pathlib.Path('codebase/code.py'),
                    excluded_lines=[],
                    covered_lines=[1, 2, 3, 5, 13, 14],
                    missing_lines=[6, 8, 10, 11],
                    info=PytestCoverageInfo(
                        covered_lines=6,
                        num_statements=10,
                        percent_covered=PytestCoverageHandler().convert_to_decimal(60.0),
                        percent_covered_display='60%',
                        missing_lines=4,
                        excluded_lines=0,
                        num_branches=3,
                        num_partial_branches=1,
                        covered_branches=1,
                        missing_branches=1,
                    ),
                    executed_branches=[[1, 0], [2, 1], [3, 0], [5, 1], [13, 0], [14, 0]],
                    missing_branches=[[6, 0], [8, 1], [10, 0], [11, 0]],
                )
            },
            info=PytestCoverageInfo(
                covered_lines=6,
                num_statements=10,
                percent_covered=PytestCoverageHandler().convert_to_decimal(60.0),
                percent_covered_display='60%',
                missing_lines=4,
                excluded_lines=0,
                num_branches=3,
                num_partial_branches=1,
                covered_branches=1,
                missing_branches=1,
            ),
        )

        assert PytestCoverageHandler().extract_info(coverage_json) == expected_coverage

    def test_get_coverage_with_branch_coverage(self, test_config, coverage_json):
        config = dataclasses.replace(test_config, BRANCH_COVERAGE=True)
        handler = PytestCoverageHandler()
        with patch('pathlib.Path.open') as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_json)
            coverage = handler.get_coverage(config=config)

        assert coverage.meta.branch_coverage is True
        assert coverage.files[pathlib.Path('codebase/code.py')].missing_branches == [[0, 11]]
