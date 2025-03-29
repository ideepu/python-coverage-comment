import dataclasses

from codecov.exceptions import (
    ApiError,
    CannotGetBranch,
    CannotGetPullRequest,
    CannotGetUser,
    CannotPostComment,
    Conflict,
    Forbidden,
    NotFound,
    Unauthorized,
    ValidationFailed,
)
from codecov.github_client import GitHubClient
from codecov.groups import Annotation
from codecov.log import log

COMMIT_MESSAGE = 'Update annotations data'


@dataclasses.dataclass
class User:
    name: str
    email: str
    login: str


class Github:
    def __init__(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        client: GitHubClient,
        repository: str,
        pr_number: int | None = None,
        ref: str | None = None,
        annotations_data_branch: str = None,
    ):
        self.client = client
        self.repository: str = repository
        self.annotations_data_branch: str | None = annotations_data_branch

        self.user: User = self._init_user()
        self.pr_number, self.base_ref = self._init_pr_number(pr_number=pr_number, ref=ref)
        self.pr_diff: str = self._init_pr_diff()

    def _init_user(self) -> User:
        log.info('Getting user details.')
        try:
            response = self.client.user.get()
            return User(
                name=response.name,
                email=response.email or f'{response.id}+{response.login}@users.noreply.github.com',
                login=response.login,
            )
        except Unauthorized as exc:
            log.error('Unauthorized access to user details. Invalid token.')
            raise CannotGetUser from exc
        except Forbidden as exc:
            log.error('Cannot get user details.')
            raise CannotGetUser from exc

    def _init_pr_number(self, pr_number: int | None = None, ref: str | None = None) -> tuple[int, str]:
        if pr_number:
            log.info('Getting pull request #%d.', pr_number)
            try:
                pull_request = self.client.repos(self.repository).pulls(pr_number).get()
                if pull_request.state != 'open':
                    log.debug('Pull request #%d is not in open state.', pr_number)
                    raise NotFound

                return pull_request.number, pull_request.head.ref
            except Forbidden as exc:
                log.error('Forbidden access to pull request #%d.', pr_number)
                raise CannotGetPullRequest from exc
            except NotFound as exc:
                log.error('Pull request #%d does not exist or not in open state.', pr_number)
                raise CannotGetPullRequest from exc

        # If we're not on a PR, we need to find the PR number from the branch name
        if ref:
            log.info('Getting pull request for branch %s.', ref)
            try:
                pull_requests = self.client.repos(self.repository).pulls.get(state='open', per_page=100)
                for pull_request in pull_requests:
                    if pull_request.head.ref == ref:
                        return pull_request.number, pull_request.head.ref
                log.debug('No open pull request found for branch %s.', ref)
                raise NotFound
            except Forbidden as exc:
                log.error('Forbidden access to pull requests for branch %s.', ref)
                raise CannotGetPullRequest from exc
            except NotFound as exc:
                log.error('Checked the recent updated 100 PRs, No open pull request found for branch %s.', ref)
                raise CannotGetPullRequest from exc

        log.error('No pull request number or branch reference provided.')
        raise CannotGetPullRequest

    def _init_pr_diff(self) -> str:
        log.debug('Getting the diff for pull request #%d.', self.pr_number)
        try:
            pull_request_diff = (
                self.client.repos(self.repository)
                .pulls(self.pr_number)
                .get(use_text=True, headers={'Accept': 'application/vnd.github.v3.diff'})
            )
        except Forbidden as exc:
            log.error('Forbidden access to pull request #%d diff.', self.pr_number)
            raise CannotGetPullRequest from exc
        except NotFound as exc:
            log.error('Pull request #%d does not exist or not in open state.', self.pr_number)
            raise CannotGetPullRequest from exc

        return pull_request_diff

    def post_comment(self, contents: str, marker: str) -> None:
        log.info('Posting comment on pull request #%d.', self.pr_number)
        if len(contents) > 65536:
            log.error('Comment exceeds allowed size(65536)')
            raise CannotPostComment

        # Pull request review comments are comments made on a portion of the unified diff during a pull request review.
        # Issue comments are comments on the entire pull request. We need issue comments.
        issue_comments_path = self.client.repos(self.repository).issues(self.pr_number).comments
        comments_path = self.client.repos(self.repository).issues.comments
        for comment in issue_comments_path.get():
            if comment.user.login == self.user.login and marker in comment.body:
                log.info('Updating existing comment on pull request')
                try:
                    comments_path(comment.id).patch(body=contents)
                    return
                except Forbidden as exc:
                    log.error('Forbidden access to update comment.')
                    raise CannotPostComment from exc
                except ApiError as exc:
                    log.error('Unknown Api error while updating comment.')
                    raise CannotPostComment from exc

        log.info('Adding new comment on pull request')
        try:
            issue_comments_path.post(body=contents)
        except Forbidden as exc:
            log.error('Forbidden access to post comment.')
            raise CannotPostComment from exc

    def write_annotations_to_branch(self, annotations: list[Annotation]) -> None:
        if not self.annotations_data_branch:
            log.debug('No annotations data branch provided. Exiting.')
            return

        log.debug('Getting the annotations data branch.')
        try:
            data_branch = self.client.repos(self.repository).branches(self.annotations_data_branch).get()
            if data_branch.protected:
                log.debug('Branch "%s/%s" is protected.', self.repository, self.annotations_data_branch)
                raise NotFound
        except Forbidden as exc:
            log.error('Forbidden access to branch "%s/%s".', self.repository, self.annotations_data_branch)
            raise CannotGetBranch from exc
        except NotFound as exc:
            log.error('Branch "%s/%s" does not exist.', self.repository, self.annotations_data_branch)
            raise CannotGetBranch from exc

        log.info('Writing annotations to branch.')
        file_name = f'{self.pr_number}-annotations.json'
        file_sha: str | None = None
        try:
            file = self.client.repos(self.repository).contents(file_name).get(ref=self.annotations_data_branch)
            file_sha = file.sha
        except NotFound:
            log.debug(
                'File "%s" does not exist in branch "%s/%s", creating new file.',
                file_name,
                self.repository,
                self.annotations_data_branch,
            )
        except Forbidden as exc:
            log.error('Forbidden access to branch "%s/%s".', self.repository, self.annotations_data_branch)
            raise CannotGetBranch from exc

        try:
            log.debug('Writing annotations to file to branch.')
            encoded_content = Annotation.encode(annotations)
            self.client.repos(self.repository).contents(file_name).put(
                message=COMMIT_MESSAGE,
                branch=self.annotations_data_branch,
                sha=file_sha,
                committer={
                    'name': self.user.name,
                    'email': self.user.email,
                },
                content=encoded_content,
            )
        except NotFound as exc:
            log.error('Branch "%s/%s" does not exist.', self.repository, self.annotations_data_branch)
            raise CannotGetBranch from exc
        except Forbidden as exc:
            log.error('Forbidden access to branch "%s/%s".', self.repository, self.annotations_data_branch)
            raise CannotGetBranch from exc
        except Conflict as exc:
            log.error('Conflict writing to branch "%s/%s".', self.repository, self.annotations_data_branch)
            raise CannotGetBranch from exc
        except ValidationFailed as exc:
            log.error('Validation failed on committer name or email.')
            raise CannotGetBranch from exc
