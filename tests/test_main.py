# -*- coding: utf-8 -*-
import json
import pathlib
import tempfile
from unittest import mock

import pytest

from codecov import diff_grouper, github, main


@mock.patch('pathlib.Path.open')
def test_process_pr_skip_coverage(
    mock_open: mock.Mock,
    base_config,
    gh,
    coverage_json,
    session,
    caplog,
):
    config = base_config(SKIP_COVERAGE=True)
    caplog.set_level('INFO')
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_json)
    diff_data = 'diff --git a/file.py b/file.py\nindex 1234567..abcdefg 100644\n--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n+bar\n-baz\n+qux\n'
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(text=diff_data)
    session.register('GET', '/user')(json={'login': 'foo', 'id': 123, 'name': 'bar', 'email': 'baz'})

    result = main.process_pr(config, gh, config.GITHUB_PR_NUMBER)

    assert result == 0
    assert caplog.records[-1].message == 'Skipping coverage report generation'


@mock.patch('pathlib.Path.open')
def test_process_pr_skip_coverage_with_annotations(
    mock_open: mock.Mock,
    base_config,
    gh,
    coverage_json,
    session,
    caplog,
):
    config = base_config(
        SKIP_COVERAGE=True,
        ANNOTATE_MISSING_LINES=True,
    )
    caplog.set_level('INFO')
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_json)
    diff_data = 'diff --git a/file.py b/file.py\nindex 1234567..abcdefg 100644\n--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n+bar\n-baz\n+qux\n'
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(text=diff_data)
    session.register('GET', '/user')(json={'login': 'foo', 'id': 123, 'name': 'bar', 'email': 'baz'})

    result = main.process_pr(config, gh, config.GITHUB_PR_NUMBER)

    assert result == 0


@mock.patch('pathlib.Path.open')
@mock.patch('codecov.main.template.read_template_file')
@mock.patch('codecov.main.github.post_comment')
def test_process_branch_coverage_in_annotations(
    mock_post_comment: mock.Mock,
    mock_read_template_file: mock.Mock,
    mock_open: mock.Mock,
    base_config,
    gh,
    coverage_json,
    session,
    caplog,
):
    config = base_config(
        ANNOTATE_MISSING_LINES=True,
        BRANCH_COVERAGE=True,
    )
    caplog.set_level('INFO')
    annotations = [
        github.Annotation(
            file=pathlib.Path('file.py'),
            line_start=10,
            line_end=10,
            title='Error',
            message_type='warning',
            message='Error',
        )
    ]
    mock_read_template_file.return_value = """
        {% block foo %}foo{% endblock foo %}
        {{ marker }}
        """
    mock_post_comment.return_value = None
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_json)
    github.create_missing_coverage_annotations = mock.Mock(return_value=annotations)
    diff_data = 'diff --git a/file.py b/file.py\nindex 1234567..abcdefg 100644\n--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n+bar\n-baz\n+qux\n'
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(text=diff_data)
    session.register('GET', '/user')(json={'login': 'foo', 'id': 123, 'name': 'bar', 'email': 'baz'})

    result = main.process_pr(config, gh, config.GITHUB_PR_NUMBER)

    assert result == 0


@mock.patch('pathlib.Path.open')
@mock.patch('codecov.template.read_template_file')
def test_process_pr_with_annotations_missing_marker_error(
    mock_read_template_file: mock.Mock,
    mock_open: mock.Mock,
    base_config,
    gh,
    coverage_json,
    session,
):
    config = base_config(SUBPROJECT_ID='sub_project')
    mock_read_template_file.return_value = """{% block foo %}foo{% endblock foo %}"""
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_json)
    diff_data = 'diff --git a/file.py b/file.py\nindex 1234567..abcdefg 100644\n--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n+bar\n-baz\n+qux\n'
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(text=diff_data)
    session.register('GET', '/user')(json={'login': 'foo', 'id': 123, 'name': 'bar', 'email': 'baz'})

    result = main.process_pr(config, gh, config.GITHUB_PR_NUMBER)

    assert result == 1


@mock.patch('pathlib.Path.open')
@mock.patch('codecov.main.template.read_template_file')
def test_process_pr_with_annotations_template_error(
    mock_read_template_file: mock.Mock,
    mock_open: mock.Mock,
    base_config,
    gh,
    coverage_json,
    session,
):
    config = base_config(
        ANNOTATE_MISSING_LINES=True,
        ANNOTATIONS_OUTPUT_PATH=pathlib.Path(tempfile.mkstemp(suffix='.json')[1]),
        SUBPROJECT_ID='sub_project',
        MINIMUM_GREEN=100,
        MINIMUM_ORANGE=80,
        COMPLETE_PROJECT_REPORT=True,
        COVERAGE_REPORT_URL='https://example.com',
    )
    mock_read_template_file.return_value = '{% for i in range(5) %}{{ i }{% endfor %}'
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_json)
    diff_data = 'diff --git a/file.py b/file.py\nindex 1234567..abcdefg 100644\n--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n+bar\n-baz\n+qux\n'
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(text=diff_data)
    session.register('GET', '/user')(json={'login': 'foo', 'id': 123, 'name': 'bar', 'email': 'baz'})

    result = main.process_pr(config, gh, config.GITHUB_PR_NUMBER)

    assert result == 1


@mock.patch('pathlib.Path.open')
@mock.patch('codecov.main.template.read_template_file')
@mock.patch('codecov.main.github.post_comment')
def test_process_pr_with_annotations_cannot_post(
    mock_post_comment: mock.Mock,
    mock_read_template_file: mock.Mock,
    mock_open: mock.Mock,
    base_config,
    gh,
    coverage_json,
    session,
):
    config = base_config(
        ANNOTATE_MISSING_LINES=True,
        ANNOTATIONS_OUTPUT_PATH=pathlib.Path(tempfile.mkstemp(suffix='.json')[1]),
        SUBPROJECT_ID='sub_project',
    )
    mock_read_template_file.return_value = """
        {% block foo %}foo{% endblock foo %}
        {{ marker }}
        """
    mock_post_comment.side_effect = github.CannotPostComment
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_json)
    diff_data = 'diff --git a/file.py b/file.py\nindex 1234567..abcdefg 100644\n--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n+bar\n-baz\n+qux\n'
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(text=diff_data)
    session.register('GET', '/user')(json={'login': 'foo', 'id': 123, 'name': 'bar', 'email': 'baz'})

    result = main.process_pr(config, gh, config.GITHUB_PR_NUMBER)

    assert result == 1
    mock_post_comment.assert_called_once()


@mock.patch('pathlib.Path.open')
@mock.patch('codecov.main.template.read_template_file')
@mock.patch('codecov.main.github.post_comment')
def test_process_pr_with_annotations(
    mock_post_comment: mock.Mock,
    mock_read_template_file: mock.Mock,
    mock_open: mock.Mock,
    base_config,
    gh,
    coverage_json,
    session,
    caplog,
):
    config = base_config(
        ANNOTATE_MISSING_LINES=True,
        ANNOTATIONS_OUTPUT_PATH=pathlib.Path(tempfile.mkstemp(suffix='.json')[1]),
        SUBPROJECT_ID='sub_project',
    )
    caplog.set_level('DEBUG')
    annotations = [
        github.Annotation(
            file=pathlib.Path('file.py'),
            line_start=10,
            line_end=10,
            title='Error',
            message_type='warning',
            message='Error',
        )
    ]
    mock_read_template_file.return_value = """
        {% block foo %}foo{% endblock foo %}
        {{ marker }}
        """
    mock_post_comment.return_value = None
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_json)
    github.create_missing_coverage_annotations = mock.Mock(return_value=annotations)
    diff_data = 'diff --git a/file.py b/file.py\nindex 1234567..abcdefg 100644\n--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n+bar\n-baz\n+qux\n'
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(text=diff_data)
    session.register('GET', '/user')(json={'login': 'foo', 'id': 123, 'name': 'bar', 'email': 'baz'})

    result = main.process_pr(config, gh, config.GITHUB_PR_NUMBER)

    assert result == 0
    assert caplog.records[-1].message == 'Comment created on PR'


@mock.patch('pathlib.Path.open')
@mock.patch('codecov.main.template.read_template_file')
@mock.patch('codecov.main.github.post_comment')
def test_process_pr_with_annotations_to_branch(
    mock_post_comment: mock.Mock,
    mock_read_template_file: mock.Mock,
    mock_open: mock.Mock,
    base_config,
    gh,
    coverage_json,
    session,
    caplog,
):
    config = base_config(
        ANNOTATE_MISSING_LINES=True,
        ANNOTATIONS_OUTPUT_PATH=pathlib.Path(tempfile.mkstemp(suffix='.json')[1]),
        SUBPROJECT_ID='sub_project',
        ANNOTATIONS_DATA_BRANCH='annotations-data',
    )
    caplog.set_level('DEBUG')
    annotations = [
        github.Annotation(
            file=pathlib.Path('file.py'),
            line_start=10,
            line_end=10,
            title='Error',
            message_type='warning',
            message='Error',
        )
    ]
    mock_read_template_file.return_value = """
        {% block foo %}foo{% endblock foo %}
        {{ marker }}
        """
    mock_post_comment.return_value = None
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_json)
    github.create_missing_coverage_annotations = mock.Mock(return_value=annotations)
    github.write_annotations_to_branch = mock.Mock(return_value=None)
    diff_data = 'diff --git a/file.py b/file.py\nindex 1234567..abcdefg 100644\n--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n+bar\n-baz\n+qux\n'
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(text=diff_data)
    session.register('GET', '/user')(json={'login': 'foo', 'id': 123, 'name': 'bar', 'email': 'baz'})

    result = main.process_pr(config, gh, config.GITHUB_PR_NUMBER)

    assert result == 0
    assert caplog.records[-1].message == 'Comment created on PR'


@mock.patch('pathlib.Path.open')
def test_process_pr_generate_annotations(mock_open: mock.Mock, gh, base_config, coverage_obj, session, coverage_json):
    config = base_config(BRANCH_COVERAGE=True)
    main.generate_annotations = mock.Mock(side_effect=github.CannotGetBranch)
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_json)
    diff_grouper.group_branches = mock.Mock(return_value=coverage_obj)
    diff_data = 'diff --git a/file.py b/file.py\nindex 1234567..abcdefg 100644\n--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n+bar\n-baz\n+qux\n'
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(text=diff_data)
    session.register('GET', '/user')(json={'login': 'foo', 'id': 123, 'name': 'bar', 'email': 'baz'})

    result = main.process_pr(
        config=config,
        pr_number=123,
        gh=gh,
    )
    assert result == 1


@mock.patch('codecov.main.settings.Config.from_environ')
@mock.patch('codecov.main.log.setup')
@mock.patch('codecov.main.sys.exit')
@mock.patch('codecov.main.httpx.Client')
@mock.patch('codecov.main.action')
def test_main_success(mock_action, mock_httpx_client, mock_sys_exit, mock_log_setup, mock_config_from_environ):
    mock_config = mock_config_from_environ.return_value
    mock_github_session = mock_httpx_client.return_value
    mock_action.return_value = 0

    main.main()

    mock_config_from_environ.assert_called_once_with(environ=mock.ANY)
    mock_log_setup.assert_called_once_with(debug=mock_config.DEBUG)
    mock_action.assert_called_once_with(config=mock_config, github_session=mock_github_session)
    mock_sys_exit.assert_called_once_with(0)


@mock.patch('codecov.main.settings.Config.from_environ')
def test_main_skip_coverage(mock_config_from_environ, base_config):
    mock_config_from_environ.return_value = base_config(SKIP_COVERAGE=True)
    with pytest.raises(SystemExit):
        main.main()


@mock.patch('codecov.main.settings.Config.from_environ')
@mock.patch('codecov.main.sys.exit')
@mock.patch('codecov.main.httpx.Client')
@mock.patch('codecov.main.action')
def test_main_exception(mock_action, mock_httpx_client, mock_sys_exit, mock_config_from_environ):
    mock_config = mock_config_from_environ.return_value
    mock_github_session = mock_httpx_client.return_value
    mock_action.side_effect = Exception()

    main.main()

    mock_config_from_environ.assert_called_once_with(environ=mock.ANY)
    mock_action.assert_called_once_with(config=mock_config, github_session=mock_github_session)
    mock_sys_exit.assert_called_once_with(1)


def test_action_pull_request_success(session, base_config):
    config = base_config()
    main.process_pr = mock.Mock(return_value=0)
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(
        json={'number': config.GITHUB_PR_NUMBER, 'state': 'open'}
    )
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}')(
        json={'default_branch': 'baz', 'visibility': 'public'}
    )

    result = main.action(config=config, github_session=session)

    assert result == 0


def test_action_pull_request_failed(session, base_config):
    config = base_config()
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(status_code=404)
    result = main.action(config=config, github_session=session)
    assert result == 1
