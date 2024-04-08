# -*- coding: utf-8 -*-
import json
import pathlib
from unittest import mock

import pytest

from codecov import github, main


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


# TODO: Fix the test cases below
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
):
    config = base_config(
        ANNOTATE_MISSING_LINES=True,
        ANNOTATIONS_OUTPUT_PATH=pathlib.Path('output.json'),
        SUBPROJECT_ID='sub_project',
    )
    mock_read_template_file.return_value = """
        {% block foo %}foo{% endblock foo %}
        {{ marker }}
        """
    mock_post_comment.return_value = None
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_json)
    diff_data = 'diff --git a/file.py b/file.py\nindex 1234567..abcdefg 100644\n--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n+bar\n-baz\n+qux\n'
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(text=diff_data)
    session.register('GET', '/user')(json={'login': 'foo'})

    repo_info = github.RepositoryInfo(default_branch='main', visibility='public')
    result = main.process_pr(config, gh, repo_info, config.GITHUB_PR_NUMBER)

    assert result == 0


@mock.patch('pathlib.Path.open')
def test_process_pr_with_annotations_skip_coverage(
    mock_open: mock.Mock,
    base_config,
    gh,
    coverage_json,
    session,
):
    config = base_config(
        ANNOTATE_MISSING_LINES=True,
        ANNOTATIONS_OUTPUT_PATH=pathlib.Path('output.json'),
        SKIP_COVERAGE=True,
    )
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(coverage_json)
    diff_data = 'diff --git a/file.py b/file.py\nindex 1234567..abcdefg 100644\n--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n+bar\n-baz\n+qux\n'
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(text=diff_data)

    repo_info = github.RepositoryInfo(default_branch='main', visibility='public')
    result = main.process_pr(config, gh, repo_info, config.GITHUB_PR_NUMBER)

    assert result == 0
