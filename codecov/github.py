# -*- coding: utf-8 -*-
import dataclasses
import json
import pathlib
from collections.abc import Iterable

from codecov import github_client, groups, log, settings

GITHUB_CODECOV_LOGIN = 'CI-codecov[bot]'


class CannotDeterminePR(Exception):
    pass


class CannotPostComment(Exception):
    pass


class CannotGetPullRequest(Exception):
    pass


class NoArtifact(Exception):
    pass


@dataclasses.dataclass
class Annotation:
    file: pathlib.Path
    line_start: int
    line_end: int
    title: str
    message_type: str
    message: str

    def __str__(self) -> str:
        return f'{self.message_type} {self.message} in {self.file}:{self.line_start}-{self.line_end}'

    def __repr__(self) -> str:
        return f'{self.message_type} {self.message} in {self.file}:{self.line_start}-{self.line_end}'

    def to_dict(self):
        return {
            'file': str(self.file),
            'line_start': self.line_start,
            'line_end': self.line_end,
            'title': self.title,
            'message_type': self.message_type,
            'message': self.message,
        }


class AnnotationEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Annotation):
            return o.to_dict()
        return super().default(o)


@dataclasses.dataclass
class RepositoryInfo:
    default_branch: str
    visibility: str

    def is_default_branch(self, ref: str) -> bool:
        return f'refs/heads/{self.default_branch}' == ref

    def is_public(self) -> bool:
        return self.visibility == 'public'


def get_repository_info(github: github_client.GitHub, repository: str) -> RepositoryInfo:
    response = github.repos(repository).get()

    return RepositoryInfo(default_branch=response.default_branch, visibility=response.visibility)


def get_my_login(github: github_client.GitHub) -> str:
    try:
        response = github.user.get()
    except github_client.Forbidden:
        # The GitHub actions user cannot access its own details
        # and I'm not sure there's a way to see that we're using
        # the GitHub actions user except noting that it fails
        return GITHUB_CODECOV_LOGIN

    return response.login


def get_pr_number(github: github_client.GitHub, config: settings.Config) -> int:
    if config.GITHUB_PR_NUMBER:
        try:
            pull_request = github.repos(config.GITHUB_REPOSITORY).pulls(config.GITHUB_PR_NUMBER).get()
            if pull_request.state != 'open':
                raise github_client.NotFound

            return pull_request.number
        except github_client.Forbidden as exc:
            raise CannotGetPullRequest from exc
        except github_client.NotFound:
            log.warning(f'Pull request #{config.GITHUB_PR_NUMBER} does not exist')
    # sdfs
    # If we're not on a PR, we need to find the PR number from the branch name
    if config.GITHUB_REF:
        try:
            pull_requests = github.repos(config.GITHUB_REPOSITORY).pulls.get(state='open', head=config.GITHUB_REF)
            if len(pull_requests) != 1:
                raise github_client.NotFound

            return pull_requests[0].number
        except github_client.Forbidden as exc:
            raise CannotGetPullRequest from exc
        except github_client.NotFound as exc:
            raise CannotGetPullRequest from exc

    raise CannotGetPullRequest(
        'This worflow is not triggered on a pull_request event, '
        "nor on a push event on a branch. Consequently, there's nothing to do. "
        'Exiting.'
    )


def get_pr_diff(github: github_client.GitHub, repository: str, pr_number: int) -> str:
    try:
        pull_request_diff = (
            github.repos(repository)
            .pulls(pr_number)
            .get(use_text=True, headers={'Accept': 'application/vnd.github.v3.diff'})
        )
    except github_client.Forbidden as exc:
        raise CannotGetPullRequest from exc
    except github_client.NotFound as exc:
        raise CannotGetPullRequest from exc

    return pull_request_diff


def post_comment(  # pylint: disable=too-many-arguments
    github: github_client.GitHub,
    me: str,
    repository: str,
    pr_number: int,
    contents: str,
    marker: str,
) -> None:
    if len(contents) > 65536:
        raise CannotPostComment('Comment exceeds allowed size(65536)')

    issue_comments_path = github.repos(repository).issues(pr_number).comments
    comments_path = github.repos(repository).issues.comments

    for comment in issue_comments_path.get():
        if comment.user.login == me and marker in comment.body:
            log.info('Update previous comment')
            try:
                comments_path(comment.id).patch(body=contents)
            except github_client.Forbidden as exc:
                raise CannotPostComment from exc
            except github_client.ApiError as exc:
                raise CannotPostComment from exc
            break
    else:
        log.info('Adding new comment')
        try:
            issue_comments_path.post(body=contents)
        except github_client.Forbidden as exc:
            raise CannotPostComment from exc


def create_missing_coverage_annotations(
    annotation_type: str,
    annotations: Iterable[groups.Group],
) -> list[Annotation]:
    """
    Create annotations for lines with missing coverage.

    annotation_type: The type of annotation to create. Can be either "error" or "warning" or "notice".
    annotations: A list of tuples of the form (file, line_start, line_end)
    """
    formatted_annotations: list[Annotation] = []
    for group in annotations:
        if group.line_start == group.line_end:
            message = f'Missing coverage on line {group.line_start}'
        else:
            message = f'Missing coverage on lines {group.line_start}-{group.line_end}'

        formatted_annotations.append(
            Annotation(
                file=group.file,
                line_start=group.line_start,
                line_end=group.line_end,
                title='Missing coverage',
                message_type=annotation_type,
                message=message,
            )
        )
    return formatted_annotations
