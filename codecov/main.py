import json
import os

from codecov import diff_grouper, groups, template
from codecov.config import Config
from codecov.coverage import PytestCoverage
from codecov.coverage.base import Coverage, DiffCoverage
from codecov.exceptions import CoreProcessingException, MissingMarker, TemplateException
from codecov.github import Github
from codecov.github_client import GitHubClient
from codecov.log import log, setup as log_setup


class Main:
    def __init__(self):
        self.config = self._init_config()
        self._init_log()
        self._init_required()
        self.github = self._init_github()
        self.coverage: Coverage
        self.diff_coverage: DiffCoverage
        # Default coverage module
        self.coverage_module = PytestCoverage()

    def _init_config(self):
        return Config.from_environ(environ=os.environ)

    def _init_log(self):
        log_setup(debug=self.config.DEBUG)

    def _init_required(self):
        if self.config.SKIP_COVERAGE and not self.config.ANNOTATE_MISSING_LINES:
            log.error('Nothing to do since both SKIP_COVERAGE and ANNOTATE_MISSING_LINES are set to False. Exiting.')
            raise CoreProcessingException

    def _init_github(self):
        gh_client = GitHubClient(token=self.config.GITHUB_TOKEN)
        github = Github(
            client=gh_client,
            repository=self.config.GITHUB_REPOSITORY,
            pr_number=self.config.GITHUB_PR_NUMBER,
            ref=self.config.GITHUB_REF,
            annotations_data_branch=self.config.ANNOTATIONS_DATA_BRANCH,
        )
        return github

    def run(self):
        self._process_coverage()
        self._process_pr()
        self._generate_annotations()

    def _process_coverage(self):
        log.info('Processing coverage data')
        coverage = self.coverage_module.get_coverage_info(coverage_path=self.config.COVERAGE_PATH)
        if self.config.BRANCH_COVERAGE:
            coverage = diff_grouper.fill_branch_missing_groups(coverage=coverage)
        added_lines = self.coverage_module.parse_diff_output(diff=self.github.pr_diff)
        diff_coverage = self.coverage_module.get_diff_coverage_info(added_lines=added_lines, coverage=coverage)
        self.coverage = coverage
        self.diff_coverage = diff_coverage

    def _process_pr(self):
        if self.config.SKIP_COVERAGE:
            log.info('Skipping coverage report generation.')
            return

        log.info('Generating comment for PR')
        marker = template.get_marker(marker_id=self.config.SUBPROJECT_ID)
        files_info, count_files, changed_files_info = template.select_changed_files(
            coverage=self.coverage,
            diff_coverage=self.diff_coverage,
            max_files=self.config.MAX_FILES_IN_COMMENT,
        )
        coverage_files_info, count_coverage_files = template.select_files(
            coverage=self.coverage,
            changed_files_info=changed_files_info,
            max_files=self.config.MAX_FILES_IN_COMMENT - count_files,  # Truncate the report to MAX_FILES_IN_COMMENT
        )
        try:
            comment = template.get_comment_markdown(
                coverage=self.coverage,
                diff_coverage=self.diff_coverage,
                files=files_info,
                count_files=count_files,
                coverage_files=coverage_files_info,
                count_coverage_files=count_coverage_files,
                max_files=self.config.MAX_FILES_IN_COMMENT,
                minimum_green=self.config.MINIMUM_GREEN,
                minimum_orange=self.config.MINIMUM_ORANGE,
                repo_name=self.config.GITHUB_REPOSITORY,
                pr_number=self.github.pr_number,
                base_ref=self.github.base_ref,
                base_template=template.read_template_file('comment.md.j2'),
                marker=marker,
                subproject_id=self.config.SUBPROJECT_ID,
                branch_coverage=self.config.BRANCH_COVERAGE,
                complete_project_report=self.config.COMPLETE_PROJECT_REPORT,
                coverage_report_url=self.config.COVERAGE_REPORT_URL,
            )
        except MissingMarker as e:
            log.error(
                'Marker not found. This error can happen if you defined a custom comment '
                "template that doesn't inherit the base template and you didn't include "
                '``{{ marker }}``. The marker is necessary for this action to recognize '
                "its own comment and avoid making new comments or overwriting someone else's "
                'comment.'
            )
            raise CoreProcessingException from e
        except TemplateException as e:
            log.error(
                'There was a rendering error when computing the text of the comment to post '
                "on the PR. Please see the traceback, in particular if you're using a custom "
                'template.'
            )
            raise CoreProcessingException from e

        self.github.post_comment(contents=comment, marker=marker)
        log.info('Comment created on PR.')

    def _generate_annotations(self):
        if not self.config.ANNOTATE_MISSING_LINES:
            log.info('Skipping annotations generation.')
            return

        log.info('Generating annotations for missing lines.')
        annotations = diff_grouper.get_diff_missing_groups(coverage=self.coverage, diff_coverage=self.diff_coverage)
        formatted_annotations = groups.create_missing_coverage_annotations(
            annotation_type=self.config.ANNOTATION_TYPE,
            annotations=annotations,
        )

        if self.config.BRANCH_COVERAGE:
            branch_annotations = diff_grouper.get_diff_branch_missing_groups(
                coverage=self.coverage,
                diff_coverage=self.diff_coverage,
            )
            formatted_annotations.extend(
                groups.create_missing_coverage_annotations(
                    annotation_type=self.config.ANNOTATION_TYPE,
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
        # TODO: Take the folder path instead of the file path
        if self.config.ANNOTATIONS_OUTPUT_PATH:
            log.info('Writing annotations to file.')
            with self.config.ANNOTATIONS_OUTPUT_PATH.open('w+') as annotations_file:
                json.dump(formatted_annotations, annotations_file, cls=groups.AnnotationEncoder)

        if self.config.ANNOTATIONS_DATA_BRANCH:
            log.info('Writing annotations to branch.')
            self.github.write_annotations_to_branch(annotations=formatted_annotations)
        log.info('Annotations generated.')
