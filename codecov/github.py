import dataclasses
import pathlib
from collections import defaultdict, deque

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
            log.error('Authentication failed. The provided token is invalid. Please verify the token.')
            raise CannotGetUser from exc
        except Forbidden as exc:
            log.error(
                'Insufficient permissions. Unable to retrieve user details with the provided token. Please verify the token permissions and try again.',
            )
            raise CannotGetUser from exc

    def _get_pr_details_from_pr_number(self, pr_number: int) -> tuple[int, str]:
        log.info('Getting pull request #%d.', pr_number)
        try:
            pull_request = self.client.repos(self.repository).pulls(pr_number).get()
            if pull_request.state != 'open':
                log.debug('Pull request #%d is not in open state.', pr_number)
                raise NotFound

            return pull_request.number, pull_request.head.ref
        except Forbidden as exc:
            log.error(
                'Forbidden access to pull request #%d. Insufficient permissions to retrieve details. Please verify the token permissions and try again.',
                pr_number,
            )

            raise CannotGetPullRequest from exc
        except NotFound as exc:
            log.error(
                'Pull request #%d could not be found or is not in an open state. Please verify the pull request status.',
                pr_number,
            )

            raise CannotGetPullRequest from exc

    def _get_pr_details_from_ref(self, ref: str) -> tuple[int, str]:
        log.info('Getting pull request for branch %s.', ref)
        try:
            pull_requests = self.client.repos(self.repository).pulls.get(state='open', per_page=100)
            for pull_request in pull_requests:
                if pull_request.head.ref == ref:
                    return pull_request.number, pull_request.head.ref
            log.debug(
                'No open pull request found for branch %s. Please ensure the branch has an active pull request.',
                ref,
            )

            raise NotFound
        except Forbidden as exc:
            log.error(
                'Forbidden access to pull requests created for branch %s. Insufficient permissions to view pull request details.',
                ref,
            )
            raise CannotGetPullRequest from exc
        except NotFound as exc:
            log.error(
                'Checked the 100 most recent PRs in the repository, but no open pull request found for branch %s.',
                ref,
            )
            raise CannotGetPullRequest from exc

    def _init_pr_number(self, pr_number: int | None = None, ref: str | None = None) -> tuple[int, str]:
        if pr_number:
            return self._get_pr_details_from_pr_number(pr_number)

        # If we're not on a PR, we need to find the PR number from the branch name
        if ref:
            return self._get_pr_details_from_ref(ref)

        log.error('Pull request number or branch reference missing.')
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
            log.error(
                'Insufficient permissions to retrieve the diff of pull request #%d. Please verify the token permissions and try again.',
                self.pr_number,
            )
            raise CannotGetPullRequest from exc
        except NotFound as exc:
            log.error(
                'Pull request #%d does not exist or is not in an open state. Please ensure the branch has an active pull request.',
                self.pr_number,
            )
            raise CannotGetPullRequest from exc

        return pull_request_diff

    def post_comment(self, contents: str, marker: str) -> None:
        log.info('Posting comment on pull request #%d.', self.pr_number)
        if len(contents) > 65536:
            log.error(
                'Comment exceeds the 65536 character limit (GitHub limitation). Reduce the number of files to be reported in the comment using "MAX_FILES_IN_COMMENT" and try again.'
            )
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
                    log.error(
                        'Insufficient permissions to update the comment on pull request #%d. Please verify the token permissions and try again.'
                    )
                    raise CannotPostComment from exc
                except ApiError as exc:
                    log.error(
                        'Error occurred while updating the comment on pull request #%d. Details: %s',
                        self.pr_number,
                        str(exc),
                    )
                    raise CannotPostComment from exc

        log.info('Adding new comment on pull request')
        try:
            issue_comments_path.post(body=contents)
        except Forbidden as exc:
            log.error(
                'Insufficient permissions to post a comment on pull request #%d. Please check the token permissions and try again.',
                self.pr_number,
            )
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
            log.error(
                'Insufficient permissions to write annotations to the branch "%s/%s". Please verify the token permissions and ensure it has content read and write access.',
                self.repository,
                self.annotations_data_branch,
            )
            raise CannotGetBranch from exc
        except NotFound as exc:
            log.error(
                'Branch "%s/%s" either does not exist or is protected.', self.repository, self.annotations_data_branch
            )
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
            log.error(
                'Insufficient permissions to write annotations to the branch "%s/%s". Please verify the token permissions and ensure it has content read and write access.',
                self.repository,
                self.annotations_data_branch,
            )
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
            log.error(
                'Branch "%s/%s" either does not exist or is protected.', self.repository, self.annotations_data_branch
            )
            raise CannotGetBranch from exc
        except Forbidden as exc:
            log.error(
                'Insufficient permissions to write annotations to the branch "%s/%s". Please verify the token permissions and ensure it has content read and write access.',
                self.repository,
                self.annotations_data_branch,
            )
            raise CannotGetBranch from exc
        except Conflict as exc:
            log.error(
                'Conflict while adding #%s pull request annotation to branch "%s/%s".',
                self.pr_number,
                self.repository,
                self.annotations_data_branch,
            )
            raise CannotGetBranch from exc
        except ValidationFailed as exc:
            log.error(
                'Validation failed for committer name or email, or the endpoint was spammed while writing annotation to branch "%s/%s".',
                self.repository,
                self.annotations_data_branch,
            )
            raise CannotGetBranch from exc


class GithubDiffParser:
    def __init__(self, diff: str):
        self.diff_lines: deque[str] = deque(diff.splitlines())
        self.added_filename_prefix = '+++ b/'
        self.result: dict[pathlib.Path, list[int]] = defaultdict(list)

    def _get_hunk_start_and_length(self, diff_line: str) -> tuple[int, int]:
        # The diff_line looks like: "@@ -60,0 +61,9 @@ ...", and we want to extract the starting line number of the added lines.
        # diff_line.split()[2] gives "+61,9" (the added lines part).
        # 61 is the starting line number of the added lines and 9 is the number of lines in the hunk (context lines + added lines).
        # [1:] removes the '+' sign, so we get "61,9".
        # Adding ',1' ensures that if there's no comma (e.g., "+61"), we still get a tuple ("61", "1").
        # .split(',') splits into ["61", "9"], and [:2] ensures we only take the first two elements.
        # The generator expression converts them to integers.
        line_no, hunk_length = (int(i) for i in (diff_line.split()[2][1:] + ',1').split(',')[:2])
        return line_no, hunk_length

    def _parse_hunk_diff_lines(self, line_no: int, hunk_length: int) -> list[int]:
        """
        Parse the "added" part of the line number diff text:
            @@ -60,0 +61 @@ def compute_files(  -> [64]
            @@ -60,0 +61,9 @@ def compute_files(  -> [64, 65, 66]

        Github API returns default context lines 3 at start and end, we need to remove them.
        This also handles the case where there are no or less context lines than expected in the hunk.
        This method gets only the added lines of the new file in the hunk, we ignore the modified lines in the original file.
        """
        added_lines: list[int] = []
        hunk_lines = list(range(line_no, line_no + hunk_length))
        while hunk_lines:
            next_line = self.diff_lines.popleft()
            # The lines without any changes start with a space. These could be context lines or unchanged lines.
            # We ignore these and consider the actual changed line as the start of diff.
            if next_line.startswith(' '):
                hunk_lines.pop(0)
                continue

            # We ignore deleted lines because they are changed/removed lines in original file and consider the the added lines of the new file as the start of diff.
            if next_line.startswith('-'):
                continue

            if next_line.startswith('+'):
                added_lines.append(hunk_lines.pop(0))

        return added_lines

    def parse(self) -> dict[pathlib.Path, list[int]]:
        current_file: pathlib.Path | None = None
        while self.diff_lines:
            line = self.diff_lines.popleft()
            if line.startswith(self.added_filename_prefix):
                current_file = pathlib.Path(line.removeprefix(self.added_filename_prefix))
                continue
            if not line.startswith('@@'):
                continue

            line_no, hunk_length = self._get_hunk_start_and_length(line)
            lines = self._parse_hunk_diff_lines(line_no=line_no, hunk_length=hunk_length)
            if len(lines) > 0:
                if current_file is None:
                    log.error('Diff output format is invalid: %s', self.diff_lines)
                    raise ValueError
                self.result[current_file].extend(lines)

        return self.result
