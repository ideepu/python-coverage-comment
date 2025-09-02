import base64
import json
import pathlib
from unittest.mock import MagicMock, patch

import pytest

from codecov.exceptions import CannotGetBranch, CannotGetPullRequest, CannotGetUser, CannotPostComment
from codecov.github import COMMIT_MESSAGE, Github, GithubDiffParser, User
from codecov.groups import Annotation, AnnotationEncoder

TEST_DATA_PR_DIFF = 'diff --git a/file.py b/file.py\nindex 1234567..abcdefg 100644\n--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n+bar\n-baz\n+qux\n'


class TestGitHub:
    @patch.object(Github, '_init_pr_diff', return_value=TEST_DATA_PR_DIFF)
    @patch.object(Github, '_init_pr_number', return_value=(123, 'feature/branch'))
    @patch.object(Github, '_init_user', return_value=User(name='bar', email='baz@foobar.com', login='foo'))
    def test_init(
        self,
        gh_init_user_mock: MagicMock,
        gh_init_pr_number_mock: MagicMock,
        gh_init_pr_diff_mock: MagicMock,
        test_config,
        gh_client,
    ):
        gh = Github(
            client=gh_client,
            repository=test_config.GITHUB_REPOSITORY,
            pr_number=test_config.GITHUB_PR_NUMBER,
            ref=test_config.GITHUB_REF,
            annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
        )
        assert gh.client == gh_client
        assert gh.repository == test_config.GITHUB_REPOSITORY
        assert gh.annotations_data_branch == test_config.ANNOTATIONS_DATA_BRANCH
        assert gh.user == User(name='bar', email='baz@foobar.com', login='foo')
        assert gh.pr_number == test_config.GITHUB_PR_NUMBER
        assert gh.base_ref == 'feature/branch'
        assert gh.pr_diff == TEST_DATA_PR_DIFF
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()

    @patch.object(Github, '_init_pr_diff', return_value=TEST_DATA_PR_DIFF)
    @patch.object(Github, '_init_pr_number', return_value=(123, 'feature/branch'))
    def test_init_user_login(
        self,
        gh_init_pr_number_mock: MagicMock,
        gh_init_pr_diff_mock: MagicMock,
        session,
        test_config,
        gh_client,
    ):
        session.register('GET', '/user')(status_code=401)
        with pytest.raises(CannotGetUser):
            Github(
                client=gh_client,
                repository=test_config.GITHUB_REPOSITORY,
                pr_number=test_config.GITHUB_PR_NUMBER,
                ref=test_config.GITHUB_REF,
                annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
            )
        gh_init_pr_number_mock.assert_not_called()
        gh_init_pr_diff_mock.assert_not_called()

        session.register('GET', '/user')(status_code=403)
        with pytest.raises(CannotGetUser):
            Github(
                client=gh_client,
                repository=test_config.GITHUB_REPOSITORY,
                pr_number=test_config.GITHUB_PR_NUMBER,
                ref=test_config.GITHUB_REF,
                annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
            )
        gh_init_pr_number_mock.assert_not_called()
        gh_init_pr_diff_mock.assert_not_called()

        session.register('GET', '/user')(json={'login': 'foo', 'id': 123, 'name': 'bar', 'email': 'baz'})
        gh = Github(
            client=gh_client,
            repository=test_config.GITHUB_REPOSITORY,
            pr_number=test_config.GITHUB_PR_NUMBER,
            ref=test_config.GITHUB_REF,
            annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
        )
        assert gh.user == User(name='bar', email='baz', login='foo')
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()

    @patch.object(Github, '_init_pr_diff', return_value=TEST_DATA_PR_DIFF)
    @patch.object(Github, '_init_user', return_value=User(name='bar', email='baz@foobar.com', login='foo'))
    def test_init_pr_number(
        self,
        gh_init_user_mock: MagicMock,
        gh_init_pr_diff_mock: MagicMock,
        session,
        test_config,
        gh_client,
    ):
        with pytest.raises(CannotGetPullRequest):
            Github(
                client=gh_client,
                repository=test_config.GITHUB_REPOSITORY,
                annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
            )
        gh_init_user_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_not_called()
        gh_init_user_mock.reset_mock()

        session.register('GET', f'/repos/{test_config.GITHUB_REPOSITORY}/pulls/{test_config.GITHUB_PR_NUMBER}')(
            json={'number': test_config.GITHUB_PR_NUMBER, 'state': 'closed'}
        )
        with pytest.raises(CannotGetPullRequest):
            Github(
                client=gh_client,
                repository=test_config.GITHUB_REPOSITORY,
                pr_number=test_config.GITHUB_PR_NUMBER,
                annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
            )
        gh_init_user_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_not_called()
        gh_init_user_mock.reset_mock()

        session.register('GET', f'/repos/{test_config.GITHUB_REPOSITORY}/pulls/{test_config.GITHUB_PR_NUMBER}')(
            status_code=403
        )
        with pytest.raises(CannotGetPullRequest):
            Github(
                client=gh_client,
                repository=test_config.GITHUB_REPOSITORY,
                pr_number=test_config.GITHUB_PR_NUMBER,
                annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
            )
        gh_init_user_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_not_called()
        gh_init_user_mock.reset_mock()

        session.register('GET', f'/repos/{test_config.GITHUB_REPOSITORY}/pulls/{test_config.GITHUB_PR_NUMBER}')(
            status_code=404
        )
        with pytest.raises(CannotGetPullRequest):
            Github(
                client=gh_client,
                repository=test_config.GITHUB_REPOSITORY,
                pr_number=test_config.GITHUB_PR_NUMBER,
                annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
            )
        gh_init_user_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_not_called()
        gh_init_user_mock.reset_mock()

        session.register('GET', f'/repos/{test_config.GITHUB_REPOSITORY}/pulls/{test_config.GITHUB_PR_NUMBER}')(
            json={'number': test_config.GITHUB_PR_NUMBER, 'head': {'ref': 'feature/branch'}, 'state': 'open'}
        )
        gh = Github(
            client=gh_client,
            repository=test_config.GITHUB_REPOSITORY,
            pr_number=test_config.GITHUB_PR_NUMBER,
            annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
        )
        assert gh.pr_number == test_config.GITHUB_PR_NUMBER
        assert gh.base_ref == 'feature/branch'
        gh_init_user_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()

    @patch.object(Github, '_init_pr_diff', return_value=TEST_DATA_PR_DIFF)
    @patch.object(Github, '_init_user', return_value=User(name='bar', email='baz@foobar.com', login='foo'))
    def test_init_pr_ref(
        self,
        gh_init_user_mock: MagicMock,
        gh_init_pr_diff_mock: MagicMock,
        session,
        test_config,
        gh_client,
    ):
        test_config.GITHUB_REF = 'feature/branch'
        session.register('GET', f'/repos/{test_config.GITHUB_REPOSITORY}/pulls')(json=[])
        with pytest.raises(CannotGetPullRequest):
            Github(
                client=gh_client,
                repository=test_config.GITHUB_REPOSITORY,
                ref=test_config.GITHUB_REF,
                annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
            )
        gh_init_user_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_not_called()
        gh_init_user_mock.reset_mock()

        session.register('GET', f'/repos/{test_config.GITHUB_REPOSITORY}/pulls')(status_code=403)
        with pytest.raises(CannotGetPullRequest):
            Github(
                client=gh_client,
                repository=test_config.GITHUB_REPOSITORY,
                ref=test_config.GITHUB_REF,
                annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
            )
        gh_init_user_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_not_called()
        gh_init_user_mock.reset_mock()

        session.register('GET', f'/repos/{test_config.GITHUB_REPOSITORY}/pulls')(status_code=404)
        with pytest.raises(CannotGetPullRequest):
            Github(
                client=gh_client,
                repository=test_config.GITHUB_REPOSITORY,
                ref=test_config.GITHUB_REF,
                annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
            )
        gh_init_user_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_not_called()
        gh_init_user_mock.reset_mock()

        session.register('GET', f'/repos/{test_config.GITHUB_REPOSITORY}/pulls')(
            json=[
                {'head': {'ref': 'feature/not-the-right-branch'}, 'number': 124, 'state': 'open'},
                {'head': {'ref': 'feature/branch'}, 'number': test_config.GITHUB_PR_NUMBER, 'state': 'open'},
            ]
        )
        gh = Github(
            client=gh_client,
            repository=test_config.GITHUB_REPOSITORY,
            ref=test_config.GITHUB_REF,
            annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
        )
        assert gh.pr_number == test_config.GITHUB_PR_NUMBER
        gh_init_user_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()

    @patch.object(Github, '_init_pr_number', return_value=(123, 'feature/branch'))
    @patch.object(Github, '_init_user', return_value=User(name='bar', email='baz@foobar.com', login='foo'))
    def test_init_pr_diff(
        self,
        gh_init_user_mock: MagicMock,
        gh_init_pr_number_mock: MagicMock,
        session,
        test_config,
        gh_client,
    ):
        session.register('GET', f'/repos/{test_config.GITHUB_REPOSITORY}/pulls/{test_config.GITHUB_PR_NUMBER}')(
            status_code=403
        )
        with pytest.raises(CannotGetPullRequest):
            Github(
                client=gh_client,
                repository=test_config.GITHUB_REPOSITORY,
                pr_number=test_config.GITHUB_PR_NUMBER,
                annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
            )
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_user_mock.reset_mock()
        gh_init_pr_number_mock.reset_mock()

        session.register('GET', f'/repos/{test_config.GITHUB_REPOSITORY}/pulls/{test_config.GITHUB_PR_NUMBER}')(
            status_code=404
        )
        with pytest.raises(CannotGetPullRequest):
            Github(
                client=gh_client,
                repository=test_config.GITHUB_REPOSITORY,
                pr_number=test_config.GITHUB_PR_NUMBER,
                annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
            )
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_user_mock.reset_mock()
        gh_init_pr_number_mock.reset_mock()

        session.register('GET', f'/repos/{test_config.GITHUB_REPOSITORY}/pulls/{test_config.GITHUB_PR_NUMBER}')(
            text=TEST_DATA_PR_DIFF
        )
        gh = Github(
            client=gh_client,
            repository=test_config.GITHUB_REPOSITORY,
            pr_number=test_config.GITHUB_PR_NUMBER,
            annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
        )
        assert gh.pr_diff == TEST_DATA_PR_DIFF
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()

    @patch.object(Github, '_init_pr_diff', return_value=TEST_DATA_PR_DIFF)
    @patch.object(Github, '_init_pr_number', return_value=(123, 'feature/branch'))
    @patch.object(Github, '_init_user', return_value=User(name='bar', email='baz@foobar.com', login='foo'))
    def test_post_comment(
        self,
        gh_init_user_mock: MagicMock,
        gh_init_pr_number_mock: MagicMock,
        gh_init_pr_diff_mock: MagicMock,
        session,
        test_config,
        gh_client,
    ):
        with pytest.raises(CannotPostComment):
            Github(
                client=gh_client,
                repository=test_config.GITHUB_REPOSITORY,
                pr_number=test_config.GITHUB_PR_NUMBER,
                annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
            ).post_comment(contents='a' * 65537, marker='marker')
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()
        gh_init_user_mock.reset_mock()
        gh_init_pr_number_mock.reset_mock()
        gh_init_pr_diff_mock.reset_mock()

        session.register(
            'GET', f'/repos/{test_config.GITHUB_REPOSITORY}/issues/{test_config.GITHUB_PR_NUMBER}/comments'
        )(json=[])
        session.register(
            'POST',
            f'/repos/{test_config.GITHUB_REPOSITORY}/issues/{test_config.GITHUB_PR_NUMBER}/comments',
            json={'body': 'hi!'},
        )(status_code=403)
        with pytest.raises(CannotPostComment):
            Github(
                client=gh_client,
                repository=test_config.GITHUB_REPOSITORY,
                pr_number=test_config.GITHUB_PR_NUMBER,
                annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
            ).post_comment(contents='hi!', marker='marker')
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()
        gh_init_user_mock.reset_mock()
        gh_init_pr_number_mock.reset_mock()
        gh_init_pr_diff_mock.reset_mock()

        session.register(
            'GET', f'/repos/{test_config.GITHUB_REPOSITORY}/issues/{test_config.GITHUB_PR_NUMBER}/comments'
        )(json=[])
        session.register(
            'POST',
            f'/repos/{test_config.GITHUB_REPOSITORY}/issues/{test_config.GITHUB_PR_NUMBER}/comments',
            json={'body': 'hi!'},
        )()
        gh = Github(
            client=gh_client,
            repository=test_config.GITHUB_REPOSITORY,
            pr_number=test_config.GITHUB_PR_NUMBER,
            annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
        )
        gh.post_comment(contents='hi!', marker='marker')
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()

    @patch.object(Github, '_init_pr_diff', return_value=TEST_DATA_PR_DIFF)
    @patch.object(Github, '_init_pr_number', return_value=(123, 'feature/branch'))
    @patch.object(Github, '_init_user', return_value=User(name='bar', email='baz@foobar.com', login='foo'))
    def test_post_comment_update(
        self,
        gh_init_user_mock: MagicMock,
        gh_init_pr_number_mock: MagicMock,
        gh_init_pr_diff_mock: MagicMock,
        session,
        test_config,
        gh_client,
    ):
        comment_with_no_marker = {
            'user': {'login': 'foo'},
            'body': 'Hey! Hi! How are you?',
            'id': 123,
        }
        comment = {
            'user': {'login': 'foo'},
            'body': 'Hey! Hi! How are you? marker',
            'id': 456,
        }
        session.register(
            'GET', f'/repos/{test_config.GITHUB_REPOSITORY}/issues/{test_config.GITHUB_PR_NUMBER}/comments'
        )(json=[comment_with_no_marker, comment])
        session.register(
            'PATCH',
            f'/repos/{test_config.GITHUB_REPOSITORY}/issues/comments/{comment["id"]}',
            json={'body': 'hi!'},
        )(status_code=403)
        with pytest.raises(CannotPostComment):
            Github(
                client=gh_client,
                repository=test_config.GITHUB_REPOSITORY,
                pr_number=test_config.GITHUB_PR_NUMBER,
                annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
            ).post_comment(contents='hi!', marker='marker')
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()
        gh_init_user_mock.reset_mock()
        gh_init_pr_number_mock.reset_mock()
        gh_init_pr_diff_mock.reset_mock()

        session.register(
            'GET', f'/repos/{test_config.GITHUB_REPOSITORY}/issues/{test_config.GITHUB_PR_NUMBER}/comments'
        )(json=[comment])
        session.register(
            'PATCH',
            f'/repos/{test_config.GITHUB_REPOSITORY}/issues/comments/{comment["id"]}',
            json={'body': 'hi!'},
        )(status_code=500)
        with pytest.raises(CannotPostComment):
            Github(
                client=gh_client,
                repository=test_config.GITHUB_REPOSITORY,
                pr_number=test_config.GITHUB_PR_NUMBER,
                annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
            ).post_comment(contents='hi!', marker='marker')
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()
        gh_init_user_mock.reset_mock()
        gh_init_pr_number_mock.reset_mock()
        gh_init_pr_diff_mock.reset_mock()

        session.register(
            'GET', f'/repos/{test_config.GITHUB_REPOSITORY}/issues/{test_config.GITHUB_PR_NUMBER}/comments'
        )(json=[comment])
        session.register(
            'PATCH',
            f'/repos/{test_config.GITHUB_REPOSITORY}/issues/comments/{comment["id"]}',
            json={'body': 'hi!'},
        )()
        gh = Github(
            client=gh_client,
            repository=test_config.GITHUB_REPOSITORY,
            pr_number=test_config.GITHUB_PR_NUMBER,
            annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
        )
        gh.post_comment(contents='hi!', marker='marker')
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()

    @patch.object(Github, '_init_pr_diff', return_value=TEST_DATA_PR_DIFF)
    @patch.object(Github, '_init_pr_number', return_value=(123, 'feature/branch'))
    @patch.object(Github, '_init_user', return_value=User(name='bar', email='baz@foobar.com', login='foo'))
    def test_write_annotations_to_branch(
        self,
        gh_init_user_mock: MagicMock,
        gh_init_pr_number_mock: MagicMock,
        gh_init_pr_diff_mock: MagicMock,
        session,
        test_config,
        gh_client,
    ):
        Github(
            client=gh_client,
            repository=test_config.GITHUB_REPOSITORY,
            pr_number=test_config.GITHUB_PR_NUMBER,
            annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
        ).write_annotations_to_branch(annotations=[])
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()
        gh_init_user_mock.reset_mock()
        gh_init_pr_number_mock.reset_mock()
        gh_init_pr_diff_mock.reset_mock()

        test_config.ANNOTATIONS_DATA_BRANCH = 'annotations'
        gh = Github(
            client=gh_client,
            repository=test_config.GITHUB_REPOSITORY,
            pr_number=test_config.GITHUB_PR_NUMBER,
            annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
        )
        session.register(
            'GET', f'/repos/{test_config.GITHUB_REPOSITORY}/branches/{test_config.ANNOTATIONS_DATA_BRANCH}'
        )(json={'protected': True})
        with pytest.raises(CannotGetBranch):
            gh.write_annotations_to_branch(annotations=[])
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()

        session.register(
            'GET', f'/repos/{test_config.GITHUB_REPOSITORY}/branches/{test_config.ANNOTATIONS_DATA_BRANCH}'
        )(status_code=403)
        with pytest.raises(CannotGetBranch):
            gh.write_annotations_to_branch(annotations=[])
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()

        session.register(
            'GET', f'/repos/{test_config.GITHUB_REPOSITORY}/branches/{test_config.ANNOTATIONS_DATA_BRANCH}'
        )(status_code=404)
        with pytest.raises(CannotGetBranch):
            gh.write_annotations_to_branch(annotations=[])
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()

        session.register(
            'GET', f'/repos/{test_config.GITHUB_REPOSITORY}/branches/{test_config.ANNOTATIONS_DATA_BRANCH}'
        )(json={'protected': False, 'name': test_config.ANNOTATIONS_DATA_BRANCH})
        session.register(
            'GET',
            f'/repos/{test_config.GITHUB_REPOSITORY}/contents/{test_config.GITHUB_PR_NUMBER}-annotations.json',
            params={'ref': test_config.ANNOTATIONS_DATA_BRANCH},
        )(status_code=403)
        with pytest.raises(CannotGetBranch):
            gh.write_annotations_to_branch(annotations=[])
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()

        annotations = [
            Annotation(
                file=pathlib.Path('file.py'),
                line_start=10,
                line_end=10,
                title='Error',
                message_type='warning',
                message='Error',
            )
        ]
        session.register(
            'GET', f'/repos/{test_config.GITHUB_REPOSITORY}/branches/{test_config.ANNOTATIONS_DATA_BRANCH}'
        )(json={'protected': False, 'name': test_config.ANNOTATIONS_DATA_BRANCH})
        session.register(
            'GET',
            f'/repos/{test_config.GITHUB_REPOSITORY}/contents/{test_config.GITHUB_PR_NUMBER}-annotations.json',
            params={'ref': test_config.ANNOTATIONS_DATA_BRANCH},
        )(status_code=404)
        session.register(
            'PUT',
            f'/repos/{test_config.GITHUB_REPOSITORY}/contents/{test_config.GITHUB_PR_NUMBER}-annotations.json',
            json={
                'message': COMMIT_MESSAGE,
                'branch': test_config.ANNOTATIONS_DATA_BRANCH,
                'sha': None,
                'committer': {'name': gh.user.name, 'email': gh.user.email},
                'content': base64.b64encode(json.dumps(annotations, cls=AnnotationEncoder).encode()).decode(),
            },
        )(json={'content': {'sha': 'abc'}})
        gh.write_annotations_to_branch(annotations=annotations)
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()

        session.register(
            'GET', f'/repos/{test_config.GITHUB_REPOSITORY}/branches/{test_config.ANNOTATIONS_DATA_BRANCH}'
        )(json={'protected': False, 'name': test_config.ANNOTATIONS_DATA_BRANCH})
        session.register(
            'GET',
            f'/repos/{test_config.GITHUB_REPOSITORY}/contents/{test_config.GITHUB_PR_NUMBER}-annotations.json',
            params={'ref': test_config.ANNOTATIONS_DATA_BRANCH},
        )(json={'sha': 'abc'})
        session.register(
            'PUT',
            f'/repos/{test_config.GITHUB_REPOSITORY}/contents/{test_config.GITHUB_PR_NUMBER}-annotations.json',
            json={
                'message': COMMIT_MESSAGE,
                'branch': test_config.ANNOTATIONS_DATA_BRANCH,
                'sha': 'abc',
                'committer': {'name': gh.user.name, 'email': gh.user.email},
                'content': base64.b64encode(json.dumps(annotations, cls=AnnotationEncoder).encode()).decode(),
            },
        )(json={'content': {'sha': 'abc'}})
        gh.write_annotations_to_branch(annotations=annotations)
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()

        session.register(
            'GET', f'/repos/{test_config.GITHUB_REPOSITORY}/branches/{test_config.ANNOTATIONS_DATA_BRANCH}'
        )(json={'protected': False, 'name': test_config.ANNOTATIONS_DATA_BRANCH})
        session.register(
            'GET',
            f'/repos/{test_config.GITHUB_REPOSITORY}/contents/{test_config.GITHUB_PR_NUMBER}-annotations.json',
            params={'ref': test_config.ANNOTATIONS_DATA_BRANCH},
        )(json={'sha': 'abc'})
        session.register(
            'PUT',
            f'/repos/{test_config.GITHUB_REPOSITORY}/contents/{test_config.GITHUB_PR_NUMBER}-annotations.json',
            json={
                'message': COMMIT_MESSAGE,
                'branch': test_config.ANNOTATIONS_DATA_BRANCH,
                'sha': 'abc',
                'committer': {'name': gh.user.name, 'email': gh.user.email},
                'content': base64.b64encode(json.dumps(annotations, cls=AnnotationEncoder).encode()).decode(),
            },
        )(status_code=404)
        with pytest.raises(CannotGetBranch):
            gh.write_annotations_to_branch(annotations=annotations)
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()

        session.register(
            'GET', f'/repos/{test_config.GITHUB_REPOSITORY}/branches/{test_config.ANNOTATIONS_DATA_BRANCH}'
        )(json={'protected': False, 'name': test_config.ANNOTATIONS_DATA_BRANCH})
        session.register(
            'GET',
            f'/repos/{test_config.GITHUB_REPOSITORY}/contents/{test_config.GITHUB_PR_NUMBER}-annotations.json',
            params={'ref': test_config.ANNOTATIONS_DATA_BRANCH},
        )(json={'sha': 'abc'})
        session.register(
            'PUT',
            f'/repos/{test_config.GITHUB_REPOSITORY}/contents/{test_config.GITHUB_PR_NUMBER}-annotations.json',
            json={
                'message': COMMIT_MESSAGE,
                'branch': test_config.ANNOTATIONS_DATA_BRANCH,
                'sha': 'abc',
                'committer': {'name': gh.user.name, 'email': gh.user.email},
                'content': base64.b64encode(json.dumps(annotations, cls=AnnotationEncoder).encode()).decode(),
            },
        )(status_code=403)
        with pytest.raises(CannotGetBranch):
            gh.write_annotations_to_branch(annotations=annotations)
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()

        session.register(
            'GET', f'/repos/{test_config.GITHUB_REPOSITORY}/branches/{test_config.ANNOTATIONS_DATA_BRANCH}'
        )(json={'protected': False, 'name': test_config.ANNOTATIONS_DATA_BRANCH})
        session.register(
            'GET',
            f'/repos/{test_config.GITHUB_REPOSITORY}/contents/{test_config.GITHUB_PR_NUMBER}-annotations.json',
            params={'ref': test_config.ANNOTATIONS_DATA_BRANCH},
        )(json={'sha': 'abc'})
        session.register(
            'PUT',
            f'/repos/{test_config.GITHUB_REPOSITORY}/contents/{test_config.GITHUB_PR_NUMBER}-annotations.json',
            json={
                'message': COMMIT_MESSAGE,
                'branch': test_config.ANNOTATIONS_DATA_BRANCH,
                'sha': 'abc',
                'committer': {'name': gh.user.name, 'email': gh.user.email},
                'content': base64.b64encode(json.dumps(annotations, cls=AnnotationEncoder).encode()).decode(),
            },
        )(status_code=409)
        with pytest.raises(CannotGetBranch):
            gh.write_annotations_to_branch(annotations=annotations)
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()

        session.register(
            'GET', f'/repos/{test_config.GITHUB_REPOSITORY}/branches/{test_config.ANNOTATIONS_DATA_BRANCH}'
        )(json={'protected': False, 'name': test_config.ANNOTATIONS_DATA_BRANCH})
        session.register(
            'GET',
            f'/repos/{test_config.GITHUB_REPOSITORY}/contents/{test_config.GITHUB_PR_NUMBER}-annotations.json',
            params={'ref': test_config.ANNOTATIONS_DATA_BRANCH},
        )(json={'sha': 'abc'})
        session.register(
            'PUT',
            f'/repos/{test_config.GITHUB_REPOSITORY}/contents/{test_config.GITHUB_PR_NUMBER}-annotations.json',
            json={
                'message': COMMIT_MESSAGE,
                'branch': test_config.ANNOTATIONS_DATA_BRANCH,
                'sha': 'abc',
                'committer': {'name': gh.user.name, 'email': gh.user.email},
                'content': base64.b64encode(json.dumps(annotations, cls=AnnotationEncoder).encode()).decode(),
            },
        )(status_code=422)
        with pytest.raises(CannotGetBranch):
            gh.write_annotations_to_branch(annotations=annotations)
        gh_init_user_mock.assert_called_once()
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()


class TestGithubDiffParser:
    @pytest.mark.parametrize(
        'line_number_diff_line, expected',
        [
            (
                'diff --git a/example.txt b/example.txt\n'
                'index abcdef1..2345678 100644\n'
                '--- a/example.txt\n'
                '+++ b/example.txt\n'
                '@@ -1,1 +1,3 @@\n'
                '-old_line_1\n'
                '+new_line_1\n'
                '+new_line_2\n'
                '+new_line_3\n'
                '@@ -10,3 +10,4 @@\n'
                '+added_line\n'
                '+added_line\n'
                '+added_line\n'
                '+added_line\n',
                {
                    pathlib.Path('example.txt'): [1, 2, 3, 10, 11, 12, 13],
                },
            ),
            (
                'diff --git a/sample.py b/sample.py\n'
                'index 1234567..abcdef1 100644\n'
                '--- a/sample.py\n'
                '+++ b/sample.py\n'
                '@@ -5,0 +5,2 @@\n'
                '+added_line_1\n'
                '+added_line_2\n'
                '@@ -20,0 +20,6 @@\n'
                '+new_function_call()\n'
                '+new_function_call()\n'
                '+new_function_call()\n'
                '+new_function_call()\n'
                '+new_function_call()\n'
                '+new_function_call()\n',
                {
                    pathlib.Path('sample.py'): [5, 6, 20, 21, 22, 23, 24, 25],
                },
            ),
            (
                'diff --git a/test.txt b/test.txt\n'
                'index 1111111..2222222 100644\n'
                '--- a/test.txt\n'
                '+++ b/test.txt\n'
                '@@ -1,1 +1,1 @@\n'
                '-old_content\n'
                '+new_content\n',
                {
                    pathlib.Path('test.txt'): [1],
                },
            ),
            (
                'diff --git a/example.py b/example.py\n'
                'index abcdef1..2345678 100644\n'
                '--- a/example.py\n'
                '+++ b/example.py\n'
                '@@ -7,4 +7,4 @@ def process_data(data):\n'
                '         if item > 0:\n'
                '             result.append(item * 2)\n'
                "-            logger.debug('Item processed: {}'.format(item))\n"
                "+            logger.info('Item processed: {}'.format(item))\n"
                '     return result\n',
                {
                    pathlib.Path('example.py'): [9],
                },
            ),
            (
                'diff --git a/sample.py b/sample.py\n'
                'index 1234567..abcdef1 100644\n'
                '--- a/sample.py\n'
                '+++ b/sample.py\n'
                '@@ -15,4 +15,5 @@ def main():\n'
                "             print('Processing item:', item)\n"
                '             result = process_item(item)\n'
                '-            if result:\n'
                "-                print('Result:', result)\n"
                "+                logger.debug('Item processed successfully')\n"
                '+            else:\n'
                "+                print('Item processing failed')\n",
                {
                    pathlib.Path('sample.py'): [17, 18, 19],
                },
            ),
            (
                'diff --git a/test.py b/test.py\n'
                'index 1111111..2222222 100644\n'
                '--- a/test.py\n'
                '+++ b/test.py\n'
                '@@ -5,4 +5,4 @@ def calculate_sum(a, b):\n'
                '     return a + b\n'
                ' def test_calculate_sum():\n'
                '+    assert calculate_sum(2, 3) == 5\n'
                '-    assert calculate_sum(0, 0) == 0\n'
                '     assert calculate_sum(-1, 1) == 0\n',
                {
                    pathlib.Path('test.py'): [7],
                },
            ),
            (
                'diff --git a/test.py b/test.py\n'
                'index 1111111..2222222 100644\n'
                '--- a/test.py\n'
                '+++ b/test.py\n'
                '@@ -5,3 +5,3 @@ def calculate_sum(a, b):\n'
                '     return a + b\n'
                ' def test_calculate_sum():\n'
                '     assert calculate_sum(-1, 1) == 0\n',
                {},
            ),
        ],
    )
    def test_parse_line_number_diff_line(self, line_number_diff_line, expected):
        result = GithubDiffParser(diff=line_number_diff_line).parse()
        assert result == expected

    def test_parse_line_number_raise_value_error(self):
        lines = (
            'diff --git a/test.py b/test.py\n'
            'index 1111111..2222222 100644\n'
            '--- a/test.py\n'
            '@@ -5,4 +5,4 @@ def calculate_sum(a, b):\n'
            '     return a + b\n'
            ' def test_calculate_sum():\n'
            '+    assert calculate_sum(2, 3) == 5\n'
            '-    assert calculate_sum(0, 0) == 0\n'
            '     assert calculate_sum(-1, 1) == 0\n'
        )
        with pytest.raises(ValueError):
            GithubDiffParser(diff=lines).parse()
