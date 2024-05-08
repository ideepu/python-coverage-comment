# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime
import decimal
import json
import pathlib
from unittest.mock import patch

import pytest

from codecov import coverage


def test_diff_violations(make_coverage_and_diff):
    _, diff = make_coverage_and_diff(
        """
        # file: a.py
        + 1 missing
        2 missing
        + 3 missing
        4 covered
        + 5 covered
        """
    )
    assert diff.files[pathlib.Path('a.py')].violation_lines == [1, 3]


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
def test_compute_coverage(num_covered, num_total, expected_coverage):
    assert coverage.compute_coverage(num_covered, num_total) == decimal.Decimal(expected_coverage)


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
            coverage.DiffCoverage(
                total_num_lines=2,
                total_num_violations=1,
                total_percent_covered=decimal.Decimal('0.5'),
                num_changed_lines=2,
                files={
                    pathlib.Path('codebase/code.py'): coverage.FileDiffCoverage(
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
            coverage.DiffCoverage(
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
            coverage.DiffCoverage(
                total_num_lines=0,
                total_num_violations=0,
                total_percent_covered=decimal.Decimal('1'),
                num_changed_lines=3,
                files={
                    pathlib.Path('codebase/code.py'): coverage.FileDiffCoverage(
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
            coverage.DiffCoverage(
                total_num_lines=4,  # 2 lines in code.py + 2 lines in other.py
                total_num_violations=1,  # 1 line in other.py
                total_percent_covered=decimal.Decimal('0.75'),  # 3/4 lines covered
                num_changed_lines=5,  # 3 lines in code.py + 2 lines in other.py
                files={
                    pathlib.Path('codebase/code.py'): coverage.FileDiffCoverage(
                        path=pathlib.Path('codebase/code.py'),
                        percent_covered=decimal.Decimal('1'),
                        added_statements=[5, 6],
                        covered_statements=[5, 6],
                        missing_statements=[],
                        added_lines=[4, 5, 6],
                    ),
                    pathlib.Path('codebase/other.py'): coverage.FileDiffCoverage(
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
def test_get_diff_coverage_info(make_coverage_obj, added_lines, update_obj, expected):
    result = coverage.get_diff_coverage_info(added_lines=added_lines, coverage=make_coverage_obj(**update_obj))
    assert result == expected


@pytest.mark.parametrize(
    'line_number_diff_line, expected',
    [
        (
            'diff --git a/example.txt b/example.txt\n'
            'index abcdef1..2345678 100644\n'
            '--- a/example.txt\n'
            '+++ b/example.txt\n'
            '@@ -1,2 +1,5 @@\n'
            '-old_line_1\n'
            '+new_line_1\n'
            '+new_line_2\n'
            '+new_line_3\n'
            '@@ -10,3 +10,4 @@\n'
            '+added_line\n'
            '+added_line\n'
            '+added_line\n'
            '+added_line\n',
            {
                pathlib.Path('example.txt'): [1, 2, 3, 10, 11, 12, 13],
            },
        ),
        (
            'diff --git a/sample.py b/sample.py\n'
            'index 1234567..abcdef1 100644\n'
            '--- a/sample.py\n'
            '+++ b/sample.py\n'
            '@@ -5,5 +5,6 @@\n'
            '+added_line_1\n'
            '+added_line_2\n'
            '@@ -20,6 +20,7 @@\n'
            '+new_function_call()\n'
            '+new_function_call()\n'
            '+new_function_call()\n'
            '+new_function_call()\n'
            '+new_function_call()\n'
            '+new_function_call()\n',
            {
                pathlib.Path('sample.py'): [5, 6, 20, 21, 22, 23, 24, 25],
            },
        ),
        (
            'diff --git a/test.txt b/test.txt\n'
            'index 1111111..2222222 100644\n'
            '--- a/test.txt\n'
            '+++ b/test.txt\n'
            '@@ -1 +1 @@\n'
            '-old_content\n'
            '+new_content\n',
            {
                pathlib.Path('test.txt'): [1],
            },
        ),
        (
            'diff --git a/example.py b/example.py\n'
            'index abcdef1..2345678 100644\n'
            '--- a/example.py\n'
            '+++ b/example.py\n'
            '@@ -7,6 +7,8 @@ def process_data(data):\n'
            '         if item > 0:\n'
            '             result.append(item * 2)\n'
            "-            logger.debug('Item processed: {}'.format(item))\n"
            "+            logger.info('Item processed: {}'.format(item))\n"
            '     return result\n',
            {
                pathlib.Path('example.py'): [9],
            },
        ),
        (
            'diff --git a/sample.py b/sample.py\n'
            'index 1234567..abcdef1 100644\n'
            '--- a/sample.py\n'
            '+++ b/sample.py\n'
            '@@ -15,6 +15,8 @@ def main():\n'
            "             print('Processing item:', item)\n"
            '             result = process_item(item)\n'
            '-            if result:\n'
            "-                print('Result:', result)\n"
            "+                logger.debug('Item processed successfully')\n"
            '+            else:\n'
            "+                print('Item processing failed')\n",
            {
                pathlib.Path('sample.py'): [17, 18, 19],
            },
        ),
        (
            'diff --git a/test.py b/test.py\n'
            'index 1111111..2222222 100644\n'
            '--- a/test.py\n'
            '+++ b/test.py\n'
            '@@ -5,5 +5,7 @@ def calculate_sum(a, b):\n'
            '     return a + b\n'
            ' def test_calculate_sum():\n'
            '+    assert calculate_sum(2, 3) == 5\n'
            '-    assert calculate_sum(0, 0) == 0\n'
            '     assert calculate_sum(-1, 1) == 0\n',
            {
                pathlib.Path('test.py'): [7],
            },
        ),
        (
            'diff --git a/test.py b/test.py\n'
            'index 1111111..2222222 100644\n'
            '--- a/test.py\n'
            '+++ b/test.py\n'
            '@@ -5,5 +5,7 @@ def calculate_sum(a, b):\n'
            '     return a + b\n'
            ' def test_calculate_sum():\n'
            '     assert calculate_sum(-1, 1) == 0\n',
            {},
        ),
    ],
)
def test_parse_line_number_diff_line(line_number_diff_line, expected):
    result = coverage.parse_diff_output(line_number_diff_line)
    assert result == expected


def test_parse_line_number_raise_value_error():
    lines = (
        'diff --git a/test.py b/test.py\n'
        'index 1111111..2222222 100644\n'
        '--- a/test.py\n'
        '@@ -5,5 +5,7 @@ def calculate_sum(a, b):\n'
        '     return a + b\n'
        ' def test_calculate_sum():\n'
        '+    assert calculate_sum(2, 3) == 5\n'
        '-    assert calculate_sum(0, 0) == 0\n'
        '     assert calculate_sum(-1, 1) == 0\n'
    )
    with pytest.raises(ValueError):
        coverage.parse_diff_output(lines)


def test_extract_info(coverage_json):
    expected_coverage = coverage.Coverage(
        meta=coverage.CoverageMetadata(
            version='1.2.3',
            timestamp=datetime.datetime.fromisoformat('2000-01-01T00:00:00'),
            branch_coverage=True,
            show_contexts=False,
        ),
        files={
            pathlib.Path('codebase/code.py'): coverage.FileCoverage(
                path=pathlib.Path('codebase/code.py'),
                excluded_lines=[],
                executed_lines=[1, 2, 3, 5, 13, 14],
                missing_lines=[6, 8, 10, 11],
                info=coverage.CoverageInfo(
                    covered_lines=6,
                    num_statements=10,
                    percent_covered=60.0,
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
        info=coverage.CoverageInfo(
            covered_lines=6,
            num_statements=10,
            percent_covered=60.0,
            percent_covered_display='60%',
            missing_lines=4,
            excluded_lines=0,
            num_branches=3,
            num_partial_branches=1,
            covered_branches=1,
            missing_branches=1,
        ),
    )

    assert coverage.extract_info(coverage_json) == expected_coverage


def test_get_coverage_info(coverage_json):
    with patch('pathlib.Path.open') as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_json)
        result = coverage.get_coverage_info(pathlib.Path('path/to/file.json'))

    assert result == coverage.extract_info(coverage_json)


def test_get_coverage_info_json_decode_error():
    with patch('pathlib.Path.open') as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = b'invalid json'
        with pytest.raises(json.JSONDecodeError):
            coverage.get_coverage_info(pathlib.Path('path/to/file.json'))


def test_get_coverage_info_file_not_found():
    with pytest.raises(FileNotFoundError):
        coverage.get_coverage_info(pathlib.Path('path/to/file.json'))
