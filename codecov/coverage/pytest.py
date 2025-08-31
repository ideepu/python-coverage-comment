from __future__ import annotations

import datetime
import pathlib

from codecov.coverage.base import BaseCoverage, Coverage, CoverageInfo, CoverageMetadata, FileCoverage


class PytestCoverage(BaseCoverage):
    def extract_info(self, data: dict) -> Coverage:
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
        return Coverage(
            meta=CoverageMetadata(
                version=data['meta']['version'],
                timestamp=datetime.datetime.fromisoformat(data['meta']['timestamp']),
                branch_coverage=data['meta']['branch_coverage'],
                show_contexts=data['meta']['show_contexts'],
            ),
            files={
                pathlib.Path(path): FileCoverage(
                    path=pathlib.Path(path),
                    excluded_lines=file_data['excluded_lines'],
                    missing_lines=file_data['missing_lines'],
                    executed_lines=file_data['executed_lines'],
                    executed_branches=file_data.get('executed_branches'),
                    missing_branches=file_data.get('missing_branches'),
                    info=CoverageInfo(
                        covered_lines=file_data['summary']['covered_lines'],
                        num_statements=file_data['summary']['num_statements'],
                        percent_covered=self.convert_to_decimal(file_data['summary']['percent_covered']),
                        percent_covered_display=file_data['summary']['percent_covered_display'],
                        missing_lines=file_data['summary']['missing_lines'],
                        excluded_lines=file_data['summary']['excluded_lines'],
                        num_branches=file_data['summary'].get('num_branches'),
                        num_partial_branches=file_data['summary'].get('num_partial_branches'),
                        covered_branches=file_data['summary'].get('covered_branches'),
                        missing_branches=file_data['summary'].get('missing_branches'),
                    ),
                )
                for path, file_data in data['files'].items()
            },
            info=CoverageInfo(
                covered_lines=data['totals']['covered_lines'],
                num_statements=data['totals']['num_statements'],
                percent_covered=self.convert_to_decimal(data['totals']['percent_covered']),
                percent_covered_display=data['totals']['percent_covered_display'],
                missing_lines=data['totals']['missing_lines'],
                excluded_lines=data['totals']['excluded_lines'],
                num_branches=data['totals'].get('num_branches'),
                num_partial_branches=data['totals'].get('num_partial_branches'),
                covered_branches=data['totals'].get('covered_branches'),
                missing_branches=data['totals'].get('missing_branches'),
            ),
        )
