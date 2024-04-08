# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
# mypy: disable-error-code="operator"
from __future__ import annotations

import datetime
import decimal
import functools
import pathlib
import secrets
from typing import Callable

import httpx
import pytest

from codecov import coverage as coverage_module, github_client, settings


@pytest.fixture
def base_config():
    def _(**kwargs):
        defaults = {
            'GITHUB_TOKEN': secrets.token_hex(16),
            'GITHUB_PR_NUMBER': 123,
            'GITHUB_REPOSITORY': 'codecov/foobar',
            'COVERAGE_PATH': pathlib.Path('coverage.json'),
        }
        return settings.Config(**(defaults | kwargs))

    return _


@pytest.fixture
def make_coverage() -> Callable[[str, bool], coverage_module.Coverage]:
    def _(code: str, has_branches: bool = True) -> coverage_module.Coverage:
        current_file = None
        coverage_obj = coverage_module.Coverage(
            meta=coverage_module.CoverageMetadata(
                version='1.2.3',
                timestamp=datetime.datetime(2000, 1, 1),
                branch_coverage=True,
                show_contexts=False,
            ),
            info=coverage_module.CoverageInfo(
                covered_lines=0,
                num_statements=0,
                percent_covered=decimal.Decimal('1.0'),
                percent_covered_display='100',
                missing_lines=0,
                excluded_lines=0,
                num_branches=0 if has_branches else None,
                num_partial_branches=0 if has_branches else None,
                covered_branches=0 if has_branches else None,
                missing_branches=0 if has_branches else None,
            ),
            files={},
        )
        line_number = 0
        # (we start at 0 because the first line will be empty for readabilty)
        for line in code.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith('# file: '):
                current_file = pathlib.Path(line.split('# file: ')[1])
                line_number = 0
                continue
            assert current_file, (line, current_file, code)
            line_number += 1
            if coverage_obj.files.get(current_file) is None:
                coverage_obj.files[current_file] = coverage_module.FileCoverage(
                    path=current_file,
                    executed_lines=[],
                    missing_lines=[],
                    excluded_lines=[],
                    info=coverage_module.CoverageInfo(
                        covered_lines=0,
                        num_statements=0,
                        percent_covered=decimal.Decimal('1.0'),
                        percent_covered_display='100',
                        missing_lines=0,
                        excluded_lines=0,
                        num_branches=0 if has_branches else None,
                        num_partial_branches=0 if has_branches else None,
                        covered_branches=0 if has_branches else None,
                        missing_branches=0 if has_branches else None,
                    ),
                )
            if set(line.split()) & {
                'covered',
                'missing',
                'excluded',
                'partial',
                'branch',
            }:
                coverage_obj.files[current_file].info.num_statements += 1
                coverage_obj.info.num_statements += 1
            if 'covered' in line or 'partial' in line:
                coverage_obj.files[current_file].executed_lines.append(line_number)
                coverage_obj.files[current_file].info.covered_lines += 1
                coverage_obj.info.covered_lines += 1
            elif 'missing' in line:
                coverage_obj.files[current_file].missing_lines.append(line_number)
                coverage_obj.files[current_file].info.missing_lines += 1
                coverage_obj.info.missing_lines += 1
            elif 'excluded' in line:
                coverage_obj.files[current_file].excluded_lines.append(line_number)
                coverage_obj.files[current_file].info.excluded_lines += 1
                coverage_obj.info.excluded_lines += 1

            if has_branches and 'branch' in line:
                coverage_obj.files[current_file].info.num_branches += 1
                coverage_obj.info.num_branches += 1
                if 'branch partial' in line:
                    coverage_obj.files[current_file].info.num_partial_branches += 1
                    coverage_obj.info.num_partial_branches += 1
                elif 'branch covered' in line:
                    coverage_obj.files[current_file].info.covered_branches += 1
                    coverage_obj.info.covered_branches += 1
                elif 'branch missing' in line:
                    coverage_obj.files[current_file].info.missing_branches += 1
                    coverage_obj.info.missing_branches += 1

            info = coverage_obj.files[current_file].info
            coverage_obj.files[current_file].info.percent_covered = coverage_module.compute_coverage(
                num_covered=info.covered_lines,
                num_total=info.num_statements,
            )
            coverage_obj.files[
                current_file
            ].info.percent_covered_display = f'{coverage_obj.files[current_file].info.percent_covered:.0%}'

            info = coverage_obj.info
            coverage_obj.info.percent_covered = coverage_module.compute_coverage(
                num_covered=info.covered_lines,
                num_total=info.num_statements,
            )
            coverage_obj.info.percent_covered_display = f'{coverage_obj.info.percent_covered:.0%}'
        return coverage_obj

    return _


@pytest.fixture
def make_diff_coverage():
    return coverage_module.get_diff_coverage_info


@pytest.fixture
def make_coverage_and_diff(
    make_coverage, make_diff_coverage
) -> Callable[[str], tuple[coverage_module.Coverage, coverage_module.DiffCoverage]]:
    def _(code: str) -> tuple[coverage_module.Coverage, coverage_module.DiffCoverage]:
        added_lines: dict[pathlib.Path, list[int]] = {}
        new_code = ''
        current_file = None
        # (we start at 0 because the first line will be empty for readabilty)
        line_number = 0
        for line in code.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith('# file: '):
                new_code += line + '\n'
                current_file = pathlib.Path(line.split('# file: ')[1])
                line_number = 0
                continue
            assert current_file
            line_number += 1

            if line.startswith('+ '):
                added_lines.setdefault(current_file, []).append(line_number)
                new_code += line[2:] + '\n'
            else:
                new_code += line + '\n'

        coverage = make_coverage('\n' + new_code)
        return coverage, make_diff_coverage(added_lines=added_lines, coverage=coverage)

    return _


@pytest.fixture
def coverage_json():
    return {
        'meta': {
            'version': '1.2.3',
            'timestamp': '2000-01-01T00:00:00',
            'branch_coverage': True,
            'show_contexts': False,
        },
        'files': {
            'codebase/code.py': {
                'executed_lines': [1, 2, 3, 5, 13, 14],
                'summary': {
                    'covered_lines': 6,
                    'num_statements': 10,
                    'percent_covered': 60.0,
                    'percent_covered_display': '60%',
                    'missing_lines': 4,
                    'excluded_lines': 0,
                    'num_branches': 3,
                    'num_partial_branches': 1,
                    'covered_branches': 1,
                    'missing_branches': 1,
                },
                'missing_lines': [6, 8, 10, 11],
                'excluded_lines': [],
            }
        },
        'totals': {
            'covered_lines': 6,
            'num_statements': 10,
            'percent_covered': 60.0,
            'percent_covered_display': '60%',
            'missing_lines': 4,
            'excluded_lines': 0,
            'num_branches': 3,
            'num_partial_branches': 1,
            'covered_branches': 1,
            'missing_branches': 1,
        },
    }


@pytest.fixture
def coverage_obj_more_files(make_coverage):
    return make_coverage(
        """
        # file: codebase/code.py
        covered
        covered
        covered

        branch partial
        missing

        missing

        branch missing
        missing

        branch covered
        covered
        # file: codebase/other.py


        missing
        covered
        missing
        missing

        missing
        covered
        covered
        """
    )


@pytest.fixture
def make_coverage_obj(coverage_obj_more_files):
    def f(**kwargs):
        obj = coverage_obj_more_files
        for key, value in kwargs.items():
            vars(obj.files[pathlib.Path(key)]).update(value)
        return obj

    return f


@pytest.fixture
def coverage_code():
    return """
        # file: codebase/code.py
        1 covered
        2 covered
        3 covered
        4
        5 branch partial
        6 missing
        7
        8 missing
        9
        10 branch missing
        11 missing
        12
        13 branch covered
        14 covered
        """


@pytest.fixture
def coverage_obj(make_coverage, coverage_code):
    return make_coverage(coverage_code)


@pytest.fixture
def diff_coverage_obj(coverage_obj, make_diff_coverage):
    return make_diff_coverage(
        added_lines={pathlib.Path('codebase/code.py'): [3, 4, 5, 6, 7, 8, 9, 12]},
        coverage=coverage_obj,
    )


@pytest.fixture
def diff_coverage_obj_more_files(coverage_obj_more_files, make_diff_coverage):
    return make_diff_coverage(
        added_lines={
            pathlib.Path('codebase/code.py'): [3, 4, 5, 6, 7, 8, 9, 12],
            pathlib.Path('codebase/other.py'): [1, 2, 3, 4, 5, 6, 7, 8, 17],
        },
        coverage=coverage_obj_more_files,
    )


@pytest.fixture
def session():
    """
    You get a session object. Register responses on it:
        session.register(method="GET", path="/a/b")(status_code=200)
    or
        session.register(method="GET", path="/a/b", json=checker)(status_code=200)
    (where checker is a function receiving the json value, and returning True if it
    matches)

    if session.request(method="GET", path="/a/b") is called, it will return a response
    with status_code 200. Also, if not called by the end of the test, it will raise.
    """

    class Session:
        def __init__(self):
            self.responses = []  # List[Tuples[request kwargs, response kwargs]]

        def request(self, method, path, **kwargs):
            request_kwargs = {'method': method, 'path': path} | kwargs

            for i, (match_kwargs, response_kwargs) in enumerate(self.responses):
                match = True
                for key, match_value in match_kwargs.items():
                    if key not in request_kwargs:
                        match = False
                        break
                    request_value = request_kwargs[key]

                    if hasattr(match_value, '__call__'):
                        try:
                            assert match_value(request_value)
                        except Exception:  # pylint: disable=broad-except
                            match = False
                            break
                    else:
                        if not match_value == request_value:
                            match = False
                            break
                if match:
                    self.responses.pop(i)
                    return httpx.Response(
                        **response_kwargs,
                        request=httpx.Request(method=method, url=path),
                    )
            assert False, f'No response found for kwargs {request_kwargs}\nExpected answers are {self.responses}'

        def __getattr__(self, value):
            if value in ['get', 'post', 'patch', 'delete', 'put']:
                return functools.partial(self.request, value.upper())
            raise AttributeError(value)

        def register(self, method, path, **request_kwargs):
            request_kwargs = {'method': method, 'path': path} | request_kwargs

            def _(**response_kwargs):
                response_kwargs.setdefault('status_code', 200)
                self.responses.append((request_kwargs, response_kwargs))

            return _

    session = Session()
    yield session


@pytest.fixture
def gh(session):
    return github_client.GitHub(session=session)
