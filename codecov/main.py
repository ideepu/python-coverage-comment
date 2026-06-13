import json
import os
from typing import cast

from codecov import diff_grouper, groups, template
from codecov.config import Config
from codecov.coverage.base import BaseCoverageHandler, DiffCoverage
from codecov.coverage.jest import JestCoverage
from codecov.coverage.pytest import PytestCoverage
from codecov.exceptions import ConfigurationException, CoreProcessingException, MissingMarker, TemplateException
from codecov.github import Github, GithubDiffParser
from codecov.github_client import GitHubClient
from codecov.log import log, setup as log_setup


class Main:
    def __init__(self):
        self.config = self._init_config()
        self._init_log()
        self.github = self._init_github()
        self.coverage_module = self._init_coverage_module()
        self.marker: str = template.MARKER
        self.comment: str = ''
        self.coverage: PytestCoverage | JestCoverage
        self.diff_coverage: DiffCoverage

    def _init_config(self) -> Config:
        return Config.from_environ(environ=os.environ)

    def _init_log(self) -> None:
        log_setup(debug=self.config.DEBUG)

    def _init_github(self) -> Github:
        gh_client = GitHubClient(token=self.config.GITHUB_TOKEN)
        github = Github(
            client=gh_client,
            repository=self.config.GITHUB_REPOSITORY,
            pr_number=self.config.GITHUB_PR_NUMBER,
            ref=self.config.GITHUB_REF,
            annotations_data_branch=self.config.ANNOTATIONS_DATA_BRANCH,
        )
        return github

    def _init_coverage_module(self) -> BaseCoverageHandler:
        try:
            return BaseCoverageHandler.get_coverage_handler(test_framework=self.config.TEST_FRAMEWORK)()
        except ConfigurationException as e:
            log.error('Error initializing coverage module. Please check the test framework and try again.')
            raise CoreProcessingException from e

    def run(self):
        self._process_coverage()
        self._render_comment_markdown()
        self._create_comment()
        self._generate_annotations()

    def _process_coverage(self):
        log.info('Processing coverage data')
        coverage = self._get_coverage()
        added_lines = GithubDiffParser(diff=self.github.pr_diff).parse()
        diff_coverage = self.coverage_module.get_diff_coverage(
            added_lines=added_lines,
            coverage=coverage,
            config=self.config,
        )
        self.coverage = coverage
        self.diff_coverage = diff_coverage

    def _get_coverage(self) -> PytestCoverage | JestCoverage:
        try:
            return self.coverage_module.get_coverage(config=self.config)
        except ConfigurationException as e:
            log.error('Error parsing the coverage file. Please check the file and try again.')
            raise CoreProcessingException from e

    def _render_comment_markdown(self) -> None:
        if self.config.SKIP_COVERAGE:
            log.info('Skipping coverage report generation.')
            return

        log.info('Generating comment for PR #%s', self.github.pr_number)
        diff_files_info, diff_count_files = template.select_changed_files(
            coverage=self.coverage,
            diff_coverage=self.diff_coverage,
            max_files=self.config.MAX_FILES_IN_COMMENT,
            skip_covered_files_in_report=self.config.SKIP_COVERED_FILES_IN_REPORT,
        )
        remaining_files = self.config.MAX_FILES_IN_COMMENT - diff_count_files
        coverage_files_info, count_coverage_files = template.select_files(
            coverage=self.coverage,
            max_files=remaining_files,  # Truncate the report to MAX_FILES_IN_COMMENT
            skip_covered_files_in_report=self.config.SKIP_COVERED_FILES_IN_REPORT,
        )
        try:
            comment = template.get_comment_markdown(
                template.read_template_file('comment.md.j2'),
                self.coverage,
                self.diff_coverage,
                self.config.MINIMUM_GREEN,
                self.config.MINIMUM_ORANGE,
                self.config.GITHUB_REPOSITORY,
                self.github.pr_number,
                self.github.base_ref,
                self.marker,
                branch_coverage=self.config.BRANCH_COVERAGE,
                complete_project_report=self.config.COMPLETE_PROJECT_REPORT,
                coverage_report_url=self.config.COVERAGE_REPORT_URL,
                max_files=self.config.MAX_FILES_IN_COMMENT,
                files=diff_files_info,
                count_files=diff_count_files,
                coverage_files=coverage_files_info,
                count_coverage_files=count_coverage_files,
            )
        except MissingMarker as e:
            log.error(
                'Marker "%s" not found. This marker is required to identify the comment and prevent creating or overwriting comments.',
                self.marker,
            )
            raise CoreProcessingException from e
        except TemplateException as e:
            log.error(
                'Rendering error occurred while generating the comment text for the PR. See the traceback for more details. Error: %s',
                str(e),
            )
            raise CoreProcessingException from e

        self.comment = comment

    def _create_comment(self):
        if not self.comment:
            log.error('Failed to generate comment, rendered template is empty.')
            raise CoreProcessingException

        self.github.post_comment(contents=self.comment, marker=self.marker)
        log.info('Comment created on PR.')

    def _generate_annotations(self):
        if not self.config.ANNOTATE_MISSING_LINES:
            log.info('Skipping annotations generation.')
            return

        log.info('Generating annotations for missing lines.')
        annotations = diff_grouper.get_diff_missing_groups(coverage=self.coverage, diff_coverage=self.diff_coverage)
        formatted_annotations = groups.create_missing_coverage_annotations(
            annotation_type=self.config.ANNOTATION_TYPE.value,
            annotations=annotations,
        )

        if self.config.BRANCH_COVERAGE:
            branch_annotations = diff_grouper.get_diff_branch_missing_groups(
                coverage=cast(PytestCoverage, self.coverage),
                diff_coverage=self.diff_coverage,
            )
            formatted_annotations.extend(
                groups.create_missing_coverage_annotations(
                    annotation_type=self.config.ANNOTATION_TYPE.value,
                    annotations=branch_annotations,
                    branch=True,
                )
            )

        if not formatted_annotations:
            log.info('No annotations to generate. Exiting.')
            return

        # Print to console
        log.info('Annotations:')
        yellow = '\033[93m'
        reset = '\033[0m'
        print(yellow, end='')
        print(*formatted_annotations, sep='\n')
        print(reset, end='')

        # Save to file
        file_name = f'{self.github.pr_number}-annotations.json'
        if self.config.ANNOTATIONS_OUTPUT_PATH:
            log.info('Writing annotations to file %s', file_name)
            with self.config.ANNOTATIONS_OUTPUT_PATH.joinpath(file_name).open('w+') as annotations_file:
                json.dump(formatted_annotations, annotations_file, cls=groups.AnnotationEncoder)

        # Write to branch
        if self.config.ANNOTATIONS_DATA_BRANCH:
            log.info('Writing annotations to branch.')
            self.github.write_annotations_to_branch(annotations=formatted_annotations)
        log.info('Annotations generated.')
