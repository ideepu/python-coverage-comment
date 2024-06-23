# -*- coding: utf-8 -*-
import base64
import dataclasses
import json
import pathlib
from collections.abc import Iterable

from codecov import github_client, groups, log, settings

GITHUB_CODECOV_LOGIN = 'CI-codecov[bot]'
COMMIT_MESSAGE = 'Update annotations data'


class CannotGetBranch(Exception):
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
        return f'{self.message_type.upper()} {self.message} in {self.file}:{self.line_start}-{self.line_end}'

    def __repr__(self) -> str:
        return f'{self.message_type.upper()} {self.message} in {self.file}:{self.line_start}-{self.line_end}'

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
class User:
    name: str
    email: str
    login: str


def get_my_login(github: github_client.GitHub) -> User:
    try:
        response = github.user.get()
        user = User(
            name=response.name,
            email=response.email or f'{response.id}+{response.login}@users.noreply.github.com',
            login=response.login,
        )
    except github_client.Forbidden:
        # The GitHub actions user cannot access its own details
        # and I'm not sure there's a way to see that we're using
        # the GitHub actions user except noting that it fails
        return User(name=GITHUB_CODECOV_LOGIN, email='', login=GITHUB_CODECOV_LOGIN)

    return user


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
    user: User,
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
        if comment.user.login == user.login and marker in comment.body:
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
    branch: bool = False,
) -> list[Annotation]:
    """
    Create annotations for lines with missing coverage.

    annotation_type: The type of annotation to create. Can be either "error" or "warning" or "notice".
    annotations: A list of tuples of the form (file, line_start, line_end)
    branch: Whether to create branch coverage annotations or not
    """
    formatted_annotations: list[Annotation] = []
    for group in annotations:
        if group.line_start == group.line_end:
            message = f'Missing {"branch " if branch else ""}coverage on line {group.line_start}'
        else:
            message = f'Missing {"branch " if branch else ""}coverage on lines {group.line_start}-{group.line_end}'

        formatted_annotations.append(
            Annotation(
                file=group.file,
                line_start=group.line_start,
                line_end=group.line_end,
                title=f'Missing {"branch " if branch else ""}coverage',
                message_type=annotation_type,
                message=message,
            )
        )
    return formatted_annotations


def write_annotations_to_branch(
    github: github_client.GitHub, user: User, pr_number: int, config: settings.Config, annotations: list[Annotation]
) -> None:
    log.info('Getting the annotations data branch.')
    try:
        data_branch = github.repos(config.GITHUB_REPOSITORY).branches(config.ANNOTATIONS_DATA_BRANCH).get()
        if data_branch.protected:
            raise github_client.NotFound
    except github_client.Forbidden as exc:
        raise CannotGetBranch from exc
    except github_client.NotFound as exc:
        log.warning(f'Branch "{config.GITHUB_REPOSITORY}/{config.ANNOTATIONS_DATA_BRANCH}" does not exist.')
        raise CannotGetBranch from exc

    log.info('Writing annotations to branch.')
    file_name = f'{pr_number}-annotations.json'
    file_sha: str | None = None
    try:
        file = github.repos(config.GITHUB_REPOSITORY).contents(file_name).get(ref=config.ANNOTATIONS_DATA_BRANCH)
        file_sha = file.sha
    except github_client.NotFound:
        pass
    except github_client.Forbidden as exc:
        log.error(f'Forbidden access to branch "{config.GITHUB_REPOSITORY}/{config.ANNOTATIONS_DATA_BRANCH}".')
        raise CannotGetBranch from exc

    try:
        encoded_content = base64.b64encode(json.dumps(annotations, cls=AnnotationEncoder).encode()).decode()
        github.repos(config.GITHUB_REPOSITORY).contents(file_name).put(
            message=COMMIT_MESSAGE,
            branch=config.ANNOTATIONS_DATA_BRANCH,
            sha=file_sha,
            committer={
                'name': user.name,
                'email': user.email,
            },
            content=encoded_content,
        )
    except github_client.NotFound as exc:
        log.error(f'Branch "{config.GITHUB_REPOSITORY}/{config.ANNOTATIONS_DATA_BRANCH}" does not exist.')
        raise CannotGetBranch from exc
    except github_client.Forbidden as exc:
        log.error(f'Forbidden access to branch "{config.GITHUB_REPOSITORY}/{config.ANNOTATIONS_DATA_BRANCH}".')
        raise CannotGetBranch from exc
    except github_client.Conflict as exc:
        log.error(f'Conflict writing to branch "{config.GITHUB_REPOSITORY}/{config.ANNOTATIONS_DATA_BRANCH}".')
        raise CannotGetBranch from exc
    except github_client.ValidationFailed as exc:
        log.error('Validation failed on committer name or email.')
        raise CannotGetBranch from exc
