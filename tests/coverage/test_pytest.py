import dataclasses
import datetime
import json
import pathlib
from unittest.mock import patch

import pytest

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
                        num_branches=7,
                        covered_branches=4,
                        missing_branches=3,
                    ),
                    executed_branches=[[2, 3], [3, 5], [5, 6], [13, 14]],
                    missing_branches=[[5, -1], [10, 11], [11, -1]],
                )
            },
            info=PytestCoverageInfo(
                covered_lines=6,
                num_statements=10,
                percent_covered=PytestCoverageHandler().convert_to_decimal(60.0),
                percent_covered_display='60%',
                missing_lines=4,
                excluded_lines=0,
                num_branches=7,
                covered_branches=4,
                missing_branches=3,
            ),
        )

        assert PytestCoverageHandler().extract_info(coverage_json) == expected_coverage

    def test_get_coverage_with_branch_coverage(self, test_config, coverage_json):
        """Branch arcs are reported as they come from the coverage report, never grouped."""
        config = dataclasses.replace(test_config, BRANCH_COVERAGE=True)
        handler = PytestCoverageHandler()
        with patch('pathlib.Path.open') as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_json)
            coverage = handler.get_coverage(config=config)

        assert coverage.meta.branch_coverage is True
        code = coverage.files[pathlib.Path('codebase/code.py')]
        assert code.missing_branches == [[5, -1], [10, 11], [11, -1]]
        assert code.executed_branches == [[2, 3], [3, 5], [5, 6], [13, 14]]

    @pytest.mark.parametrize(
        'branches, added_lines, expected',
        [
            (None, {1, 2}, []),
            ([], {1, 2}, []),
            # The source line decides whether the arc belongs to the diff, so an arc
            # pointing at an added line from an untouched line is left out.
            ([[2, 3], [4, 5]], {2, 3}, [[2, 3]]),
            # An arc leaving the enclosing scope has a negative destination.
            ([[2, -1], [4, -1]], {4}, [[4, -1]]),
            # A loop branches backwards.
            ([[7, 6]], {7}, [[7, 6]]),
            ([[2, 3], [4, 5]], set(), []),
        ],
    )
    def test_select_diff_branches(self, branches, added_lines, expected):
        assert PytestCoverageHandler.select_diff_branches(branches, added_lines) == expected
