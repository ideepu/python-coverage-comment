# -*- coding: utf-8 -*-
import json
import os
import sys

import httpx

from codecov import coverage as coverage_module, diff_grouper, github, github_client, log, settings, template


def main():
    try:
        config = settings.Config.from_environ(environ=os.environ)
        log.setup(debug=config.DEBUG)

        if config.SKIP_COVERAGE and not config.ANNOTATE_MISSING_LINES:
            log.info('Nothing to do since both SKIP_COVERAGE and ANNOTATE_MISSING_LINES are set to False. Exiting.')
            sys.exit(0)

        log.info('Starting...')
        github_session = httpx.Client(
            base_url=github_client.BASE_URL,
            follow_redirects=True,
            headers={'Authorization': f'token {config.GITHUB_TOKEN}'},
        )

        exit_code = action(config=config, github_session=github_session)
        log.info('Ending...')
        sys.exit(exit_code)

    except Exception:  # pylint: disable=broad-except
        log.error(
            'Critical error. This error possibly occurred because the permissions of the workflow are set incorrectly.'
        )
        sys.exit(1)


def action(config: settings.Config, github_session: httpx.Client) -> int:
    log.debug('Fetching Pull Request')
    gh = github_client.GitHub(session=github_session)
    try:
        pr_number = github.get_pr_number(github=gh, config=config)
    except github.CannotGetPullRequest:
        log.error('Cannot get pull request number. Exiting.', exc_info=True)
        log.error(
            'This worflow is not triggered on a pull_request event, '
            "nor on a push event on a branch. Consequently, there's nothing to do. "
            'Exiting.'
        )
        return 1

    log.debug(f'Operating on Pull Request {pr_number}')
    return process_pr(
        config=config,
        gh=gh,
        pr_number=pr_number,
    )


def process_pr(  # pylint: disable=too-many-locals
    config: settings.Config,
    gh: github_client.GitHub,
    pr_number: int,
) -> int:
    coverage = coverage_module.get_coverage_info(coverage_path=config.COVERAGE_PATH)
    if config.BRANCH_COVERAGE:
        coverage = diff_grouper.group_branches(coverage=coverage)
    pr_diff = github.get_pr_diff(github=gh, repository=config.GITHUB_REPOSITORY, pr_number=pr_number)
    added_lines = coverage_module.parse_diff_output(diff=pr_diff)
    diff_coverage = coverage_module.get_diff_coverage_info(added_lines=added_lines, coverage=coverage)

    user: github.User = github.get_my_login(github=gh)
    try:
        generate_annotations(
            config=config, user=user, pr_number=pr_number, gh=gh, coverage=coverage, diff_coverage=diff_coverage
        )
    except github.CannotGetBranch:
        log.error(
            'Cannot retrieve the annotation data branch.'
            'Please ensure it exists and that you have sufficient permissions and branch protection is disabled. Exiting.',
            exc_info=True,
        )
        return 1

    if config.SKIP_COVERAGE:
        log.info('Skipping coverage report generation')
        return 0

    log.info('Generating comment for PR')
    marker = template.get_marker(marker_id=config.SUBPROJECT_ID)
    files_info, count_files, changed_files_info = template.select_changed_files(
        coverage=coverage,
        diff_coverage=diff_coverage,
        max_files=config.MAX_FILES_IN_COMMENT,
    )
    coverage_files_info, count_coverage_files = template.select_files(
        coverage=coverage,
        changed_files_info=changed_files_info,
        max_files=config.MAX_FILES_IN_COMMENT - count_files,  # Truncate the report to MAX_FILES_IN_COMMENT
    )
    try:
        comment = template.get_comment_markdown(
            coverage=coverage,
            diff_coverage=diff_coverage,
            files=files_info,
            count_files=count_files,
            coverage_files=coverage_files_info,
            count_coverage_files=count_coverage_files,
            max_files=config.MAX_FILES_IN_COMMENT,
            minimum_green=config.MINIMUM_GREEN,
            minimum_orange=config.MINIMUM_ORANGE,
            repo_name=config.GITHUB_REPOSITORY,
            pr_number=pr_number,
            base_ref=config.GITHUB_BASE_REF,
            base_template=template.read_template_file('comment.md.j2'),
            marker=marker,
            subproject_id=config.SUBPROJECT_ID,
            branch_coverage=config.BRANCH_COVERAGE,
            complete_project_report=config.COMPLETE_PROJECT_REPORT,
            coverage_report_url=config.COVERAGE_REPORT_URL,
        )
    except template.MissingMarker:
        log.error(
            'Marker not found. This error can happen if you defined a custom comment '
            "template that doesn't inherit the base template and you didn't include "
            '``{{ marker }}``. The marker is necessary for this action to recognize '
            "its own comment and avoid making new comments or overwriting someone else's "
            'comment.'
        )
        return 1
    except template.TemplateError:
        log.error(
            'There was a rendering error when computing the text of the comment to post '
            "on the PR. Please see the traceback, in particular if you're using a custom "
            'template.'
        )
        return 1

    try:
        github.post_comment(
            github=gh,
            user=user,
            repository=config.GITHUB_REPOSITORY,
            pr_number=pr_number,
            contents=comment,
            marker=marker,
        )
    except github.CannotPostComment:
        log.debug('Exception when posting comment', exc_info=True)
        log.info(
            'Cannot post comment. This is probably because of body contents reached maximum allowed length in the comment'
        )
        return 1

    log.debug('Comment created on PR')
    return 0


def generate_annotations(  # pylint: disable=too-many-arguments
    config: settings.Config, user: github.User, pr_number: int, gh: github_client.GitHub, coverage, diff_coverage
):
    if not config.ANNOTATE_MISSING_LINES:
        return

    log.info('Generating annotations for missing lines.')
    annotations = diff_grouper.get_diff_missing_groups(coverage=coverage, diff_coverage=diff_coverage)
    formatted_annotations = github.create_missing_coverage_annotations(
        annotation_type=config.ANNOTATION_TYPE,
        annotations=annotations,
    )

    if config.BRANCH_COVERAGE:
        branch_annotations = diff_grouper.get_branch_missing_groups(coverage=coverage, diff_coverage=diff_coverage)
        formatted_annotations.extend(
            github.create_missing_coverage_annotations(
                annotation_type=config.ANNOTATION_TYPE,
                annotations=branch_annotations,
                branch=True,
            )
        )

    if not formatted_annotations:
        log.info('No annotations to generate. Exiting.')
        return

    # Print to console
    yellow = '\033[93m'
    reset = '\033[0m'
    print(yellow, end='')
    print(*formatted_annotations, sep='\n')
    print(reset, end='')

    # Save to file
    if config.ANNOTATIONS_OUTPUT_PATH:
        log.info('Writing annotations to file.')
        with config.ANNOTATIONS_OUTPUT_PATH.open('w+') as annotations_file:
            json.dump(formatted_annotations, annotations_file, cls=github.AnnotationEncoder)

    if config.ANNOTATIONS_DATA_BRANCH:
        log.info('Writing annotations to branch.')
        github.write_annotations_to_branch(
            github=gh,
            user=user,
            pr_number=pr_number,
            config=config,
            annotations=formatted_annotations,
        )
    log.info('Annotations generated.')
