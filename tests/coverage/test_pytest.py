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
                show_contexts=False,
            ),
            files={
                pathlib.Path('codebase/code.py'): PytestFileCoverage(
                    path=pathlib.Path('codebase/code.py'),
                    excluded_lines=[],
                    covered_lines=[2, 3, 5, 13, 14],
                    missing_lines=[1, 6, 8, 10, 11],
                    info=PytestCoverageInfo(
                        covered_lines=5,
                        num_statements=10,
                        percent_covered=PytestCoverageHandler().convert_to_decimal(60.0),
                        percent_covered_display='60%',
                        missing_lines=5,
                        excluded_lines=0,
                    ),
                )
            },
            info=PytestCoverageInfo(
                covered_lines=5,
                num_statements=10,
                percent_covered=PytestCoverageHandler().convert_to_decimal(60.0),
                percent_covered_display='60%',
                missing_lines=5,
                excluded_lines=0,
            ),
        )

        assert PytestCoverageHandler().extract_info(coverage_json) == expected_coverage

    def test_get_coverage_incorporates_branch_missing(self, test_config, coverage_json):
        handler = PytestCoverageHandler()
        with patch('pathlib.Path.open') as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_json)
            coverage = handler.get_coverage(config=test_config)

        assert coverage.files[pathlib.Path('codebase/code.py')].missing_lines == [1, 6, 8, 10, 11]
        assert coverage.files[pathlib.Path('codebase/code.py')].covered_lines == [2, 3, 5, 13, 14]
