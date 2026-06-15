import pathlib
from unittest.mock import MagicMock, patch

import pytest

from codecov import template
from codecov.coverage.pytest import PytestCoverageHandler
from codecov.exceptions import ConfigurationException, CoreProcessingException, MissingMarker, TemplateException
from codecov.main import Main


class TestMain:
    def test_init_with_exception(self, test_config, gh):
        with patch.object(Main, '_init_config', return_value=test_config):
            with patch.object(Main, '_init_github', return_value=gh):
                with patch(
                    'codecov.main.BaseCoverageHandler.get_coverage_handler',
                    side_effect=ConfigurationException,
                ):
                    with pytest.raises(CoreProcessingException):
                        Main()

    def test_init(self, test_config, gh):
        with patch('codecov.main.Config.from_environ', return_value=test_config):
            with patch('codecov.main.Github', return_value=gh):
                main = Main()
                assert main.config == test_config
                assert main.github.client.token == test_config.GITHUB_TOKEN
                assert main.github.repository == test_config.GITHUB_REPOSITORY
                assert main.github.pr_number == test_config.GITHUB_PR_NUMBER
                assert isinstance(main.coverage_module, PytestCoverageHandler)

    def test_process_coverage(self, test_config, gh, coverage_obj, diff_coverage_obj):
        with patch.object(Main, '_init_config', return_value=test_config):
            with patch.object(Main, '_init_github', return_value=gh):
                main = Main()
                main.coverage_module = MagicMock()
                main.coverage_module.get_coverage = MagicMock(side_effect=ConfigurationException)
                with pytest.raises(CoreProcessingException):
                    main._process_coverage()

        with patch.object(Main, '_init_config', return_value=test_config):
            with patch.object(Main, '_init_github', return_value=gh):
                main = Main()
                main.coverage_module = MagicMock()
                main.coverage_module.get_coverage = MagicMock(return_value=coverage_obj)
                main.coverage_module.get_diff_coverage = MagicMock(return_value=diff_coverage_obj)

                main._process_coverage()

                assert main.coverage == coverage_obj
                assert main.diff_coverage == diff_coverage_obj
                main.coverage_module.get_coverage.assert_called_once_with(config=test_config)
                main.coverage_module.get_diff_coverage.assert_called_once_with(
                    added_lines={pathlib.Path('codebase/code.py'): [1]},
                    coverage=coverage_obj,
                    config=test_config,
                )

    @patch('codecov.main.template.get_comment_markdown')
    def test_create_comment(
        self,
        get_comment_markdown_mock: MagicMock,
        test_config,
        gh,
        coverage_obj,
        diff_coverage_obj,
    ):
        get_comment_markdown_mock.side_effect = MissingMarker
        with patch.object(Main, '_init_config', return_value=test_config):
            with patch.object(Main, '_init_github', return_value=gh):
                with pytest.raises(CoreProcessingException):
                    main = Main()
                    main.coverage = coverage_obj
                    main.diff_coverage = diff_coverage_obj
                    main._create_comment()

        get_comment_markdown_mock.side_effect = TemplateException
        with patch.object(Main, '_init_config', return_value=test_config):
            with patch.object(Main, '_init_github', return_value=gh):
                with pytest.raises(CoreProcessingException):
                    main = Main()
                    main.coverage = coverage_obj
                    main.diff_coverage = diff_coverage_obj
                    main._create_comment()

        get_comment_markdown_mock.reset_mock()
        get_comment_markdown_mock.return_value = ''
        with patch.object(Main, '_init_config', return_value=test_config):
            with patch.object(Main, '_init_github', return_value=gh):
                main = Main()
                main.coverage = coverage_obj
                main.diff_coverage = diff_coverage_obj
                with pytest.raises(CoreProcessingException):
                    main._create_comment()

        get_comment_markdown_mock.reset_mock(side_effect=True)
        get_comment_markdown_mock.return_value = 'sample comment'
        with patch.object(Main, '_init_config', return_value=test_config):
            with patch.object(Main, '_init_github', return_value=gh):
                main = Main()
                main.coverage = coverage_obj
                main.diff_coverage = diff_coverage_obj
                main._create_comment()
                gh.post_comment.assert_called_once_with(
                    contents='sample comment',
                    marker=template.MARKER,
                )

    @patch('codecov.main.groups.create_missing_coverage_annotations')
    def test_generate_annotations_empty(
        self,
        create_missing_coverage_annotations_mock: MagicMock,
        test_config,
        gh,
        coverage_obj,
        diff_coverage_obj,
    ):
        with patch.object(Main, '_init_config', return_value=test_config):
            with patch.object(Main, '_init_github', return_value=gh):
                main = Main()
                main.config.ANNOTATE_MISSING_LINES = False
                assert main._generate_annotations() is None

        create_missing_coverage_annotations_mock.return_value = []
        with patch.object(Main, '_init_config', return_value=test_config):
            with patch.object(Main, '_init_github', return_value=gh):
                main = Main()
                main.config.ANNOTATE_MISSING_LINES = True
                main.coverage = coverage_obj
                main.diff_coverage = diff_coverage_obj
                assert main._generate_annotations() is None

    def test_generate_annotations(self, test_config, gh, coverage_obj, diff_coverage_obj):
        with patch.object(Main, '_init_config', return_value=test_config):
            with patch.object(Main, '_init_github', return_value=gh):
                main = Main()
                main.config.ANNOTATE_MISSING_LINES = True
                main.coverage = coverage_obj
                main.diff_coverage = diff_coverage_obj
                assert main._generate_annotations() is None

    def test_run(self, test_config, gh):
        with patch.object(Main, '_init_config', return_value=test_config):
            with patch.object(Main, '_init_github', return_value=gh):
                main = Main()
                main._process_coverage = MagicMock()
                main._create_comment = MagicMock()
                main._generate_annotations = MagicMock()

                assert main.run() is None

                main._process_coverage.assert_called_once()
                main._create_comment.assert_called_once()
                main._generate_annotations.assert_called_once()
