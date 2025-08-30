# pylint: disable=redefined-outer-name
# mypy: disable-error-code="operator, union-attr"
from __future__ import annotations

import datetime
import decimal
import functools
import pathlib
import secrets
from typing import Callable
from unittest.mock import MagicMock

import httpx
import pytest

from codecov.config import Config
from codecov.coverage import Coverage, CoverageInfo, CoverageMetadata, DiffCoverage, FileCoverage, PytestCoverage
from codecov.github_client import GitHubClient


@pytest.fixture
def test_config() -> Config:
    def _(**kwargs):
        defaults = {
            'GITHUB_TOKEN': secrets.token_hex(16),
            'GITHUB_PR_NUMBER': 123,
            'GITHUB_REPOSITORY': 'example/foobar',
            'COVERAGE_PATH': pathlib.Path('coverage.json'),
        }
        return Config(**(defaults | kwargs))

    return _()


@pytest.fixture
def make_coverage() -> Callable[[str, bool], Coverage]:
    def _(code: str, has_branches: bool = True) -> Coverage:
        current_file = None
        coverage_obj = Coverage(
            meta=CoverageMetadata(
                version='1.2.3',
                timestamp=datetime.datetime(2000, 1, 1),
                branch_coverage=True,
                show_contexts=False,
            ),
            info=CoverageInfo(
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
                coverage_obj.files[current_file] = FileCoverage(
                    path=current_file,
                    executed_lines=[],
                    missing_lines=[],
                    excluded_lines=[],
                    info=CoverageInfo(
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
                    executed_branches=[],
                    missing_branches=[],
                )
            if any(
                x in line
                for x in (
                    'line covered',
                    'line missing',
                    'line excluded',
                    'branch covered',
                    'branch missing',
                    'branch partial',
                )
            ):
                coverage_obj.files[current_file].info.num_statements += 1
                coverage_obj.info.num_statements += 1
            if 'line covered' in line:
                coverage_obj.files[current_file].executed_lines.append(line_number)
                coverage_obj.files[current_file].info.covered_lines += 1
                coverage_obj.info.covered_lines += 1
            elif 'line missing' in line:
                coverage_obj.files[current_file].missing_lines.append(line_number)
                coverage_obj.files[current_file].info.missing_lines += 1
                coverage_obj.info.missing_lines += 1
            elif 'line excluded' in line:
                coverage_obj.files[current_file].excluded_lines.append(line_number)
                coverage_obj.files[current_file].info.excluded_lines += 1
                coverage_obj.info.excluded_lines += 1

            if has_branches and 'branch' in line:
                coverage_obj.files[current_file].info.num_branches += 1
                coverage_obj.info.num_branches += 1
                coverage_obj.files[current_file].executed_branches.append([line_number, line_number + 1])
                if 'branch partial' in line:
                    # Even if it's partially covered, it's still considered as a missing branch
                    coverage_obj.files[current_file].missing_branches.append([line_number, line_number + 1])
                    coverage_obj.files[current_file].info.num_partial_branches += 1
                    coverage_obj.info.num_partial_branches += 1
                elif 'branch covered' in line:
                    coverage_obj.files[current_file].info.covered_branches += 1
                    coverage_obj.info.covered_branches += 1
                elif 'branch missing' in line:
                    coverage_obj.files[current_file].missing_branches.append([line_number, line_number + 1])
                    coverage_obj.files[current_file].info.missing_branches += 1
                    coverage_obj.info.missing_branches += 1

            info = coverage_obj.files[current_file].info
            coverage_obj.files[current_file].info.percent_covered = PytestCoverage().compute_coverage(
                num_covered=info.covered_lines,
                num_total=info.num_statements,
            )
            coverage_obj.files[
                current_file
            ].info.percent_covered_display = f'{coverage_obj.files[current_file].info.percent_covered:.0%}'

            info = coverage_obj.info
            coverage_obj.info.percent_covered = PytestCoverage().compute_coverage(
                num_covered=info.covered_lines,
                num_total=info.num_statements,
            )
            coverage_obj.info.percent_covered_display = f'{coverage_obj.info.percent_covered:.0%}'
        return coverage_obj

    return _


@pytest.fixture
def make_diff_coverage():
    return PytestCoverage().get_diff_coverage_info


@pytest.fixture
def make_coverage_and_diff(make_coverage, make_diff_coverage) -> Callable[[str], tuple[Coverage, DiffCoverage]]:
    def _(code: str) -> tuple[Coverage, DiffCoverage]:
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
                'executed_branches': [[1, 0], [2, 1], [3, 0], [5, 1], [13, 0], [14, 0]],
                'missing_branches': [[6, 0], [8, 1], [10, 0], [11, 0]],
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
        1 line covered
        2 line covered
        3 line covered
        4
        5 branch partial
        6 line missing
        7
        8 line missing
        9
        10 branch missing
        11 line missing
        12
        13 branch covered
        14 line covered
        # file: codebase/other.py
        1
        2 line missing
        3 branch partial
        4 line covered
        5 branch partial
        6 line missing
        7 line missing
        8
        9 line missing
        10 branch missing
        11 line covered
        12 line covered
        13 branch covered
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
        1 line covered
        2 line covered
        3 line covered
        4
        5 branch partial
        6 line missing
        7
        8 line missing
        9
        10 branch missing
        11 line missing
        12
        13 branch covered
        14 line covered
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
                        if match_value != request_value:
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
def gh_client(session, test_config: Config) -> GitHubClient:
    github_client = GitHubClient(token=test_config.GITHUB_TOKEN)
    github_client.session = session
    return github_client


@pytest.fixture
def gh(gh_client, test_config: Config):
    github_mock = MagicMock()
    github_mock.client = gh_client
    github_mock.repository = test_config.GITHUB_REPOSITORY
    github_mock.annotations_data_branch = test_config.ANNOTATIONS_DATA_BRANCH
    github_mock.pr_number = test_config.GITHUB_PR_NUMBER
    github_mock.base_ref = test_config.GITHUB_REF
    github_mock.pr_diff = 'diff --git a/codebase/code.py b/codebase/code.py\nindex 0000000..1111111 100644\n--- a/codebase/code.py\n+++ b/codebase/code.py\n@@ -1,2 +1,3 @@\n+line added\n line covered\n line covered\n'
    github_mock.user = MagicMock()
    github_mock.user.name = 'bar'
    github_mock.user.email = 'baz@foobar.com'
    github_mock.user.login = 'foo'
    github_mock.post_comment = MagicMock(return_value=None)
    github_mock.write_annotations_to_branch = MagicMock(return_value=None)
    return github_mock
