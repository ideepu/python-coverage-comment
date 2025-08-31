from __future__ import annotations

import decimal
import json
import pathlib
import tempfile
from unittest.mock import patch

import pytest

from codecov.coverage import Coverage, DiffCoverage, FileDiffCoverage
from codecov.coverage.base import BaseCoverage
from codecov.exceptions import ConfigurationException


class BaseCoverageDemo(BaseCoverage):
    def extract_info(self, data):
        del data
        return Coverage(meta=None, info=None, files={})


class TestBase:
    @pytest.mark.parametrize(
        'num_covered, num_total, expected_coverage',
        [
            (0, 10, '0'),
            (0, 0, '1'),
            (5, 0, '1'),
            (5, 10, '0.5'),
            (1, 100, '0.01'),
        ],
    )
    def test_compute_coverage(self, num_covered, num_total, expected_coverage):
        assert BaseCoverageDemo().compute_coverage(num_covered, num_total) == decimal.Decimal(expected_coverage)

    def test_get_coverage_info(self, coverage_json):
        with patch('pathlib.Path.open') as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_json)
            result = BaseCoverageDemo().get_coverage_info(pathlib.Path(tempfile.mkstemp(suffix='.json')[1]))
            assert result == BaseCoverageDemo().extract_info(coverage_json)

        with patch('pathlib.Path.open') as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b'invalid json'
            with pytest.raises(ConfigurationException):
                BaseCoverageDemo().get_coverage_info(pathlib.Path(tempfile.mkstemp(suffix='.json')[1]))

        with pytest.raises(ConfigurationException):
            BaseCoverageDemo().get_coverage_info(pathlib.Path('path/to/file.json'))

    @pytest.mark.parametrize(
        'added_lines, update_obj, expected',
        [
            # A first simple example. We added lines 1 and 3 to a file. Coverage
            # info says that lines 1 and 2 were executed and line 3 was not.
            # Diff coverage should report that the violation is line 3 and
            # that the total coverage is 50%.
            (
                {pathlib.Path('codebase/code.py'): [1, 3]},
                {'codebase/code.py': {'executed_lines': [1, 2], 'missing_lines': [3]}},
                DiffCoverage(
                    total_num_lines=2,
                    total_num_violations=1,
                    total_percent_covered=decimal.Decimal('0.5'),
                    num_changed_lines=2,
                    files={
                        pathlib.Path('codebase/code.py'): FileDiffCoverage(
                            path=pathlib.Path('codebase/code.py'),
                            percent_covered=decimal.Decimal('0.5'),
                            added_statements=[1, 3],
                            covered_statements=[1],
                            missing_statements=[3],
                            added_lines=[1, 3],
                        )
                    },
                ),
            ),
            # A second simple example. This time, the only modified file (code2.py)
            # is not the same as the files that received coverage info (code.py).
            # Consequently, no line should be reported as a violation (we could
            # imagine that the file code2.py only contains comments and is not
            # covered, nor imported.)
            (
                {pathlib.Path('codebase/code2.py'): [1, 3]},
                {'codebase/code.py': {'executed_lines': [1, 2], 'missing_lines': [3]}},
                DiffCoverage(
                    total_num_lines=0,
                    total_num_violations=0,
                    total_percent_covered=decimal.Decimal('1'),
                    num_changed_lines=2,
                    files={},
                ),
            ),
            # A third simple example. This time, there's no intersection between
            # the modified files and the files that received coverage info. We
            # should not report any violation (and 100% coverage)
            (
                {pathlib.Path('codebase/code.py'): [4, 5, 6]},
                {'codebase/code.py': {'executed_lines': [1, 2, 3], 'missing_lines': [7]}},
                DiffCoverage(
                    total_num_lines=0,
                    total_num_violations=0,
                    total_percent_covered=decimal.Decimal('1'),
                    num_changed_lines=3,
                    files={
                        pathlib.Path('codebase/code.py'): FileDiffCoverage(
                            path=pathlib.Path('codebase/code.py'),
                            percent_covered=decimal.Decimal('1'),
                            added_statements=[],
                            covered_statements=[],
                            missing_statements=[],
                            added_lines=[4, 5, 6],
                        )
                    },
                ),
            ),
            # A more complex example with 2 distinct files. We want to check both
            # that they are individually handled correctly and that the general
            # stats are correct.
            (
                {
                    pathlib.Path('codebase/code.py'): [4, 5, 6],
                    pathlib.Path('codebase/other.py'): [10, 13],
                },
                {
                    'codebase/code.py': {
                        'executed_lines': [1, 2, 3, 5, 6],
                        'missing_lines': [7],
                    },
                    'codebase/other.py': {
                        'executed_lines': [10, 11, 12],
                        'missing_lines': [13],
                    },
                },
                DiffCoverage(
                    total_num_lines=4,  # 2 lines in code.py + 2 lines in other.py
                    total_num_violations=1,  # 1 line in other.py
                    total_percent_covered=decimal.Decimal('0.75'),  # 3/4 lines covered
                    num_changed_lines=5,  # 3 lines in code.py + 2 lines in other.py
                    files={
                        pathlib.Path('codebase/code.py'): FileDiffCoverage(
                            path=pathlib.Path('codebase/code.py'),
                            percent_covered=decimal.Decimal('1'),
                            added_statements=[5, 6],
                            covered_statements=[5, 6],
                            missing_statements=[],
                            added_lines=[4, 5, 6],
                        ),
                        pathlib.Path('codebase/other.py'): FileDiffCoverage(
                            path=pathlib.Path('codebase/other.py'),
                            percent_covered=decimal.Decimal('0.5'),
                            added_statements=[10, 13],
                            covered_statements=[10],
                            missing_statements=[13],
                            added_lines=[10, 13],
                        ),
                    },
                ),
            ),
        ],
    )
    def test_get_diff_coverage_info(self, make_coverage_obj, added_lines, update_obj, expected):
        result = BaseCoverageDemo().get_diff_coverage_info(
            added_lines=added_lines,
            coverage=make_coverage_obj(**update_obj),
        )
        assert result == expected
