# -*- coding: utf-8 -*-
from __future__ import annotations

import decimal
import pathlib
import tempfile

import pytest

from codecov import settings


def test_path_below_existing_file():
    with tempfile.NamedTemporaryFile(suffix='.json') as temp_file:
        path = pathlib.Path(temp_file.name)
        assert settings.path_below(path) == path.resolve()


def test_path_below_nonexistent_file():
    path = pathlib.Path('/path/to/nonexistent_file.json')
    with pytest.raises(ValueError):
        settings.path_below(path)


def test_path_below_directory():
    path = pathlib.Path('/path/to/directory')
    with pytest.raises(ValueError):
        settings.path_below(path)


def test_path_below_non_json_file():
    with tempfile.NamedTemporaryFile(suffix='.txt') as temp_file:
        path = pathlib.Path(temp_file.name)
        with pytest.raises(ValueError):
            settings.path_below(path)


def test_config_from_environ_missing():
    with pytest.raises(settings.MissingEnvironmentVariable):
        settings.Config.from_environ({})


def test_config__from_environ__sample():
    with tempfile.NamedTemporaryFile(suffix='.json') as temp_file:
        assert settings.Config.from_environ(
            {
                'GITHUB_BASE_REF': 'main',
                'GITHUB_TOKEN': 'your_token',
                'GITHUB_REPOSITORY': 'your_repository',
                'COVERAGE_PATH': temp_file.name,
                'GITHUB_REF': 'main',
                'GITHUB_PR_NUMBER': '123',
                'SUBPROJECT_ID': 'your_subproject_id',
                'MINIMUM_GREEN': '90',
                'MINIMUM_ORANGE': '70',
                'SKIP_COVERAGE': 'False',
                'ANNOTATE_MISSING_LINES': 'True',
                'ANNOTATION_TYPE': 'warning',
                'ANNOTATIONS_OUTPUT_PATH': '/path/to/annotations',
                'MAX_FILES_IN_COMMENT': 25,
                'COMPLETE_PROJECT_REPORT': 'True',
                'COVERAGE_REPORT_URL': 'https://your_coverage_report_url',
                'DEBUG': 'False',
            }
        ) == settings.Config(
            GITHUB_REPOSITORY='your_repository',
            COVERAGE_PATH=pathlib.Path(temp_file.name).resolve(),
            GITHUB_TOKEN='your_token',  # noqa: S106
            GITHUB_PR_NUMBER=123,
            GITHUB_REF='main',
            GITHUB_BASE_REF='main',
            SUBPROJECT_ID='your_subproject_id',
            MINIMUM_GREEN=decimal.Decimal('90'),
            MINIMUM_ORANGE=decimal.Decimal('70'),
            SKIP_COVERAGE=False,
            ANNOTATE_MISSING_LINES=True,
            ANNOTATION_TYPE='warning',
            ANNOTATIONS_OUTPUT_PATH=pathlib.Path('/path/to/annotations'),
            MAX_FILES_IN_COMMENT=25,
            COMPLETE_PROJECT_REPORT=True,
            COVERAGE_REPORT_URL='https://your_coverage_report_url',
            DEBUG=False,
        )


def test_config_required_pr_or_ref():
    with tempfile.NamedTemporaryFile(suffix='.json') as temp_file:
        with pytest.raises(ValueError):
            settings.Config.from_environ(
                {
                    'GITHUB_TOKEN': 'your_token',
                    'GITHUB_REPOSITORY': 'your_repository',
                    'COVERAGE_PATH': temp_file.name,
                }
            )


def test_config_invalid_annotation_type():
    with pytest.raises(settings.InvalidAnnotationType):
        settings.Config.from_environ({'ANNOTATION_TYPE': 'foo'})


@pytest.mark.parametrize(
    'input_data, output_data',
    [
        ('true', True),
        ('True', True),
        ('1', True),
        ('yes', True),
        ('false', False),
        ('False', False),
        ('0', False),
        ('no', False),
        ('foo', False),
    ],
)
def test_str_to_bool(input_data, output_data):
    assert settings.str_to_bool(input_data) is output_data


def test_config_clean_minimum_green():
    value = settings.Config.clean_minimum_green('90')
    assert value == decimal.Decimal('90')


def test_config_clean_minimum_orange():
    value = settings.Config.clean_minimum_orange('70')
    assert value == decimal.Decimal('70')


def test_config_clean_annotate_missing_lines():
    value = settings.Config.clean_annotate_missing_lines('True')
    assert value is True


def test_config_clean_skip_coverage():
    value = settings.Config.clean_skip_coverage('False')
    assert value is False


def test_config_clean_branch_coverage():
    value = settings.Config.clean_branch_coverage('False')
    assert value is False


def test_config_clean_complete_project_report():
    value = settings.Config.clean_complete_project_report('True')
    assert value is True


def test_config_clean_debug():
    value = settings.Config.clean_debug('False')
    assert value is False


def test_config_clean_annotation_type():
    value = settings.Config.clean_annotation_type('warning')
    assert value == 'warning'


def test_config_clean_annotation_type_invalid():
    with pytest.raises(settings.InvalidAnnotationType):
        settings.Config.clean_annotation_type('foo')


def test_config_clean_github_pr_number():
    value = settings.Config.clean_github_pr_number('123')
    assert value == 123


def test_config_clean_coverage_path():
    with tempfile.NamedTemporaryFile(suffix='.json') as temp_file:
        value = settings.Config.clean_coverage_path(temp_file.name)
        assert value == pathlib.Path(temp_file.name).resolve()


def test_config_clean_annotations_output_path():
    value = settings.Config.clean_annotations_output_path('/path/to/annotations')
    assert value == pathlib.Path('/path/to/annotations')


def test_str_to_bool_invalid():
    assert settings.str_to_bool('invalid') is False


def test_config_required_clean_env_var_error():
    with tempfile.NamedTemporaryFile(suffix='.json') as temp_file:
        with pytest.raises(ValueError):
            settings.Config.from_environ(
                {
                    'GITHUB_TOKEN': 'your_token',
                    'GITHUB_REPOSITORY': 'your_repository',
                    'COVERAGE_PATH': temp_file.name,
                    'GITHUB_PR_NUMBER': 'invalid',
                }
            )
