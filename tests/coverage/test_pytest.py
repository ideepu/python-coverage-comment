# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime
import pathlib

from codecov.coverage import Coverage, CoverageInfo, CoverageMetadata, FileCoverage, PytestCoverage


class TestPytestCoverage:
    def test_extract_info(self, coverage_json):
        expected_coverage = Coverage(
            meta=CoverageMetadata(
                version='1.2.3',
                timestamp=datetime.datetime.fromisoformat('2000-01-01T00:00:00'),
                branch_coverage=True,
                show_contexts=False,
            ),
            files={
                pathlib.Path('codebase/code.py'): FileCoverage(
                    path=pathlib.Path('codebase/code.py'),
                    excluded_lines=[],
                    executed_lines=[1, 2, 3, 5, 13, 14],
                    missing_lines=[6, 8, 10, 11],
                    info=CoverageInfo(
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
            info=CoverageInfo(
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

        assert PytestCoverage().extract_info(coverage_json) == expected_coverage
