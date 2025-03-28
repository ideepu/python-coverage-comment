from __future__ import annotations

import base64
import json
import pathlib
from unittest.mock import MagicMock, patch

import pytest

from codecov.exceptions import CannotGetBranch, CannotGetPullRequest, CannotPostComment
from codecov.github import COMMIT_MESSAGE, GITHUB_CODECOV_LOGIN, Github, User
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
        session.register('GET', '/user')(status_code=403)
        gh = Github(
            client=gh_client,
            repository=test_config.GITHUB_REPOSITORY,
            pr_number=test_config.GITHUB_PR_NUMBER,
            ref=test_config.GITHUB_REF,
            annotations_data_branch=test_config.ANNOTATIONS_DATA_BRANCH,
        )
        assert gh.user == User(name=GITHUB_CODECOV_LOGIN, email='', login=GITHUB_CODECOV_LOGIN)
        gh_init_pr_number_mock.assert_called_once()
        gh_init_pr_diff_mock.assert_called_once()
        gh_init_pr_number_mock.reset_mock()
        gh_init_pr_diff_mock.reset_mock()

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
        comment = {
            'user': {'login': 'foo'},
            'body': 'Hey! Hi! How are you? marker',
            'id': 456,
        }
        session.register(
            'GET', f'/repos/{test_config.GITHUB_REPOSITORY}/issues/{test_config.GITHUB_PR_NUMBER}/comments'
        )(json=[comment])
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
