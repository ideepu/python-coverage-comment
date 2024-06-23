# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import json
import pathlib

import pytest

from codecov import github, groups


def test_get_pr(gh, session, base_config):
    config = base_config()
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(
        json={'number': config.GITHUB_PR_NUMBER, 'state': 'open'}
    )

    result = github.get_pr_number(github=gh, config=config)
    assert result == config.GITHUB_PR_NUMBER


def test_get_pr_no_open_pr(gh, session, base_config):
    config = base_config()
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(
        json={'number': config.GITHUB_PR_NUMBER, 'state': 'closed'}
    )

    with pytest.raises(github.CannotGetPullRequest):
        github.get_pr_number(github=gh, config=config)


def test_get_pr_forbidden(gh, session, base_config):
    config = base_config()
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(status_code=403)

    with pytest.raises(github.CannotGetPullRequest):
        github.get_pr_number(github=gh, config=config)


def test_get_pr_for_branch(gh, session, base_config):
    config = base_config(GITHUB_PR_NUMBER=None, GITHUB_REF='featuer/branch')
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls')(
        json=[{'number': config.GITHUB_PR_NUMBER, 'state': 'open'}]
    )

    result = github.get_pr_number(github=gh, config=config)
    assert result == config.GITHUB_PR_NUMBER


def test_get_pr_for_branch_no_open_pr(gh, session, base_config):
    config = base_config(GITHUB_PR_NUMBER=None, GITHUB_REF='featuer/branch')
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls')(json=[])

    with pytest.raises(github.CannotGetPullRequest):
        github.get_pr_number(github=gh, config=config)


def test_get_pr_for_branch_forbidden(gh, session, base_config):
    config = base_config(GITHUB_PR_NUMBER=None, GITHUB_REF='featuer/branch')
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls')(status_code=403)

    with pytest.raises(github.CannotGetPullRequest):
        github.get_pr_number(github=gh, config=config)


def test_get_pr_diff(gh, session, base_config):
    config = base_config()
    diff_data = 'diff --git a/file.py b/file.py\nindex 1234567..abcdefg 100644\n--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-foo\n+bar\n-baz\n+qux\n'
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(text=diff_data)

    result = github.get_pr_diff(github=gh, repository=config.GITHUB_REPOSITORY, pr_number=config.GITHUB_PR_NUMBER)
    assert result == diff_data


def test_get_pr_diff_forbidden(gh, session, base_config):
    config = base_config()
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(status_code=403)

    with pytest.raises(github.CannotGetPullRequest):
        github.get_pr_diff(github=gh, repository=config.GITHUB_REPOSITORY, pr_number=config.GITHUB_PR_NUMBER)


def test_get_pr_diff_not_found(gh, session, base_config):
    config = base_config()
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/pulls/{config.GITHUB_PR_NUMBER}')(status_code=404)

    with pytest.raises(github.CannotGetPullRequest):
        github.get_pr_diff(github=gh, repository=config.GITHUB_REPOSITORY, pr_number=config.GITHUB_PR_NUMBER)


def test_get_my_login(gh, session):
    session.register('GET', '/user')(json={'login': 'foo', 'id': 123, 'name': 'bar', 'email': 'baz'})
    result = github.get_my_login(github=gh)
    assert result == github.User(name='bar', email='baz', login='foo')


def test_get_my_login_github_bot(gh, session):
    session.register('GET', '/user')(status_code=403)
    result = github.get_my_login(github=gh)
    assert result == github.User(name=github.GITHUB_CODECOV_LOGIN, email='', login=github.GITHUB_CODECOV_LOGIN)


@pytest.mark.parametrize(
    'existing_comments',
    [
        [],
        [{'user': {'login': 'foo'}, 'body': 'Hey! hi! how are you?', 'id': 456}],
        [{'user': {'login': 'bar'}, 'body': 'Hey marker!', 'id': 456}],
    ],
)
def test_post_comment_create(gh, session, existing_comments):
    session.register('GET', '/repos/foo/bar/issues/123/comments')(json=existing_comments)
    session.register('POST', '/repos/foo/bar/issues/123/comments', json={'body': 'hi!'})()

    github.post_comment(
        github=gh,
        user=github.User(name='foo', email='bar', login='foo'),
        repository='foo/bar',
        pr_number=123,
        contents='hi!',
        marker='marker',
    )


def test_post_comment_content_too_long_error(gh, session):
    session.register('GET', '/repos/foo/bar/issues/123/comments')(json=[])
    session.register('POST', '/repos/foo/bar/issues/123/comments', json={'body': 'hi!'})(status_code=403)

    with pytest.raises(github.CannotPostComment):
        github.post_comment(
            github=gh,
            user=github.User(name='foo', email='bar', login='foo'),
            repository='foo/bar',
            pr_number=123,
            contents='a' * 65537,
            marker='marker',
        )


def test_post_comment_create_error(gh, session):
    session.register('GET', '/repos/foo/bar/issues/123/comments')(json=[])
    session.register('POST', '/repos/foo/bar/issues/123/comments', json={'body': 'hi!'})(status_code=403)

    with pytest.raises(github.CannotPostComment):
        github.post_comment(
            github=gh,
            user=github.User(name='foo', email='bar', login='foo'),
            repository='foo/bar',
            pr_number=123,
            contents='hi!',
            marker='marker',
        )


def test_post_comment_update(gh, session):
    comment = {
        'user': {'login': 'foo'},
        'body': 'Hey! Hi! How are you? marker',
        'id': 456,
    }
    session.register('GET', '/repos/foo/bar/issues/123/comments')(json=[comment])
    session.register('PATCH', '/repos/foo/bar/issues/comments/456', json={'body': 'hi!'})()

    github.post_comment(
        github=gh,
        user=github.User(name='foo', email='bar', login='foo'),
        repository='foo/bar',
        pr_number=123,
        contents='hi!',
        marker='marker',
    )


def test_post_comment_update_error(gh, session):
    comment = {
        'user': {'login': 'foo'},
        'body': 'Hey! Hi! How are you? marker',
        'id': 456,
    }
    session.register('GET', '/repos/foo/bar/issues/123/comments')(json=[comment])
    session.register('PATCH', '/repos/foo/bar/issues/comments/456', json={'body': 'hi!'})(status_code=403)

    with pytest.raises(github.CannotPostComment):
        github.post_comment(
            github=gh,
            user=github.User(name='foo', email='bar', login='foo'),
            repository='foo/bar',
            pr_number=123,
            contents='hi!',
            marker='marker',
        )


def test_post_comment_server_error(gh, session):
    comment = {
        'user': {'login': 'foo'},
        'body': 'Hey! Hi! How are you? marker',
        'id': 456,
    }
    session.register('GET', '/repos/foo/bar/issues/123/comments')(json=[comment])
    session.register('PATCH', '/repos/foo/bar/issues/comments/456', json={'body': 'hi!'})(status_code=500)

    with pytest.raises(github.CannotPostComment):
        github.post_comment(
            github=gh,
            user=github.User(name='foo', email='bar', login='foo'),
            repository='foo/bar',
            pr_number=123,
            contents='hi!',
            marker='marker',
        )


def test_annotation_str():
    file = pathlib.Path('/path/to/file.py')
    annotation = github.Annotation(
        file=file, line_start=10, line_end=15, title='Error', message_type='ERROR', message='Something went wrong'
    )
    expected_str = 'ERROR Something went wrong in /path/to/file.py:10-15'
    assert str(annotation) == expected_str


def test_annotation_repr():
    file = pathlib.Path('/path/to/file.py')
    annotation = github.Annotation(
        file=file, line_start=10, line_end=15, title='Error', message_type='ERROR', message='Something went wrong'
    )
    expected_repr = 'ERROR Something went wrong in /path/to/file.py:10-15'
    assert repr(annotation) == expected_repr


def test_annotation_to_dict():
    file = pathlib.Path('/path/to/file.py')
    annotation = github.Annotation(
        file=file, line_start=10, line_end=15, title='Error', message_type='ERROR', message='Something went wrong'
    )
    expected_dict = {
        'file': '/path/to/file.py',
        'line_start': 10,
        'line_end': 15,
        'title': 'Error',
        'message_type': 'ERROR',
        'message': 'Something went wrong',
    }
    assert annotation.to_dict() == expected_dict


def test_annotation_encoder_annotation():
    encoder = github.AnnotationEncoder()
    annotation = github.Annotation(
        file='/path/to/file.py',
        line_start=10,
        line_end=15,
        title='Error',
        message_type='ERROR',
        message='Something went wrong',
    )
    expected_dict = {
        'file': '/path/to/file.py',
        'line_start': 10,
        'line_end': 15,
        'title': 'Error',
        'message_type': 'ERROR',
        'message': 'Something went wrong',
    }
    result = encoder.default(annotation)
    assert result == expected_dict


def test_annotation_encoder_json():
    annotation = github.Annotation(
        file=pathlib.Path('/path/to/file.py'),
        line_start=10,
        line_end=15,
        title='Error',
        message_type='ERROR',
        message='Something went wrong',
    )
    expected_json = '{"file": "/path/to/file.py", "line_start": 10, "line_end": 15, "title": "Error", "message_type": "ERROR", "message": "Something went wrong"}'
    result = json.dumps(annotation, cls=github.AnnotationEncoder)
    assert result == expected_json


def test_non_annotation_encoder():
    sample = {
        'file': 'test_file',
        'line_start': 1,
        'line_end': 2,
        'title': 'Test Annotation',
        'message_type': 'warning',
        'message': 'This is a test annotation.',
    }

    with pytest.raises(TypeError):
        github.AnnotationEncoder().default(sample)


@pytest.mark.parametrize(
    'annotation_type, annotations, expected_annotations',
    [
        ('error', [], []),
        (
            'error',
            [groups.Group(file=pathlib.Path('file.py'), line_start=10, line_end=10)],
            [
                github.Annotation(
                    file=pathlib.Path('file.py'),
                    line_start=10,
                    line_end=10,
                    title='Missing coverage',
                    message_type='error',
                    message='Missing coverage on line 10',
                )
            ],
        ),
        (
            'warning',
            [groups.Group(file=pathlib.Path('file.py'), line_start=5, line_end=10)],
            [
                github.Annotation(
                    file=pathlib.Path('file.py'),
                    line_start=5,
                    line_end=10,
                    title='Missing coverage',
                    message_type='warning',
                    message='Missing coverage on lines 5-10',
                )
            ],
        ),
        (
            'notice',
            [
                groups.Group(file=pathlib.Path('file1.py'), line_start=5, line_end=5),
                groups.Group(file=pathlib.Path('file2.py'), line_start=10, line_end=15),
            ],
            [
                github.Annotation(
                    file=pathlib.Path('file1.py'),
                    line_start=5,
                    line_end=5,
                    title='Missing coverage',
                    message_type='notice',
                    message='Missing coverage on line 5',
                ),
                github.Annotation(
                    file=pathlib.Path('file2.py'),
                    line_start=10,
                    line_end=15,
                    title='Missing coverage',
                    message_type='notice',
                    message='Missing coverage on lines 10-15',
                ),
            ],
        ),
    ],
)
def test_create_missing_coverage_annotations(annotation_type, annotations, expected_annotations):
    assert github.create_missing_coverage_annotations(annotation_type, annotations) == expected_annotations


def test_write_annotations_to_branch_protected_branch(gh, session, base_config):
    config = base_config(ANNOTATIONS_DATA_BRANCH='annotations', ANNOTATE_MISSING_LINES=True)
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/branches/{config.ANNOTATIONS_DATA_BRANCH}')(
        json={'protected': True}
    )
    with pytest.raises(github.CannotGetBranch):
        github.write_annotations_to_branch(
            github=gh,
            user=github.User(name='foo', email='bar', login='foo'),
            pr_number=123,
            config=config,
            annotations=[],
        )


def test_write_annotations_to_branch_forbidden(gh, session, base_config):
    config = base_config(ANNOTATIONS_DATA_BRANCH='annotations', ANNOTATE_MISSING_LINES=True)
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/branches/{config.ANNOTATIONS_DATA_BRANCH}')(
        status_code=403
    )
    with pytest.raises(github.CannotGetBranch):
        github.write_annotations_to_branch(
            github=gh,
            user=github.User(name='foo', email='bar', login='foo'),
            pr_number=123,
            config=config,
            annotations=[],
        )


def test_write_annotations_to_branch_get_annotations_forbidden(gh, session, base_config):
    config = base_config(ANNOTATIONS_DATA_BRANCH='annotations', ANNOTATE_MISSING_LINES=True)
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/branches/{config.ANNOTATIONS_DATA_BRANCH}')(
        json={'protected': False, 'name': 'annotations'}
    )
    session.register(
        'GET', f'/repos/{config.GITHUB_REPOSITORY}/contents/123-annotations.json', params={'ref': 'annotations'}
    )(status_code=403)
    with pytest.raises(github.CannotGetBranch):
        github.write_annotations_to_branch(
            github=gh,
            user=github.User(name='foo', email='bar', login='foo'),
            pr_number=123,
            config=config,
            annotations=[],
        )


def test_write_annotations_to_branch_annotations_create(gh, session, base_config):
    config = base_config(ANNOTATIONS_DATA_BRANCH='annotations', ANNOTATE_MISSING_LINES=True)
    annotations = [
        github.Annotation(
            file=pathlib.Path('file.py'),
            line_start=10,
            line_end=10,
            title='Error',
            message_type='warning',
            message='Error',
        )
    ]
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/branches/{config.ANNOTATIONS_DATA_BRANCH}')(
        json={'protected': False, 'name': config.ANNOTATIONS_DATA_BRANCH}
    )
    session.register(
        'GET', f'/repos/{config.GITHUB_REPOSITORY}/contents/123-annotations.json', params={'ref': 'annotations'}
    )(status_code=404)
    session.register(
        'PUT',
        f'/repos/{config.GITHUB_REPOSITORY}/contents/123-annotations.json',
        json={
            'message': github.COMMIT_MESSAGE,
            'branch': config.ANNOTATIONS_DATA_BRANCH,
            'sha': None,
            'committer': {'name': 'foo', 'email': 'bar'},
            'content': base64.b64encode(json.dumps(annotations, cls=github.AnnotationEncoder).encode()).decode(),
        },
    )(json={'content': {'sha': 'abc'}})

    github.write_annotations_to_branch(
        github=gh,
        user=github.User(name='foo', email='bar', login='foo'),
        pr_number=123,
        config=config,
        annotations=annotations,
    )


def test_write_annotations_to_branch_annotations_update(gh, session, base_config):
    config = base_config(ANNOTATIONS_DATA_BRANCH='annotations', ANNOTATE_MISSING_LINES=True)
    annotations = [
        github.Annotation(
            file=pathlib.Path('file.py'),
            line_start=10,
            line_end=10,
            title='Error',
            message_type='warning',
            message='Error',
        )
    ]
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/branches/{config.ANNOTATIONS_DATA_BRANCH}')(
        json={'protected': False, 'name': config.ANNOTATIONS_DATA_BRANCH}
    )
    session.register(
        'GET', f'/repos/{config.GITHUB_REPOSITORY}/contents/123-annotations.json', params={'ref': 'annotations'}
    )(json={'sha': 'abc'})
    session.register(
        'PUT',
        f'/repos/{config.GITHUB_REPOSITORY}/contents/123-annotations.json',
        json={
            'message': github.COMMIT_MESSAGE,
            'branch': config.ANNOTATIONS_DATA_BRANCH,
            'sha': 'abc',
            'committer': {'name': 'foo', 'email': 'bar'},
            'content': base64.b64encode(json.dumps(annotations, cls=github.AnnotationEncoder).encode()).decode(),
        },
    )(json={'content': {'sha': 'abc'}})

    github.write_annotations_to_branch(
        github=gh,
        user=github.User(name='foo', email='bar', login='foo'),
        pr_number=123,
        config=config,
        annotations=annotations,
    )


def test_write_annotations_to_branch_annotations_update_not_found(gh, session, base_config):
    config = base_config(ANNOTATIONS_DATA_BRANCH='annotations', ANNOTATE_MISSING_LINES=True)
    annotations = [
        github.Annotation(
            file=pathlib.Path('file.py'),
            line_start=10,
            line_end=10,
            title='Error',
            message_type='warning',
            message='Error',
        )
    ]
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/branches/{config.ANNOTATIONS_DATA_BRANCH}')(
        json={'protected': False, 'name': config.ANNOTATIONS_DATA_BRANCH}
    )
    session.register(
        'GET', f'/repos/{config.GITHUB_REPOSITORY}/contents/123-annotations.json', params={'ref': 'annotations'}
    )(json={'sha': 'abc'})
    session.register(
        'PUT',
        f'/repos/{config.GITHUB_REPOSITORY}/contents/123-annotations.json',
        json={
            'message': github.COMMIT_MESSAGE,
            'branch': config.ANNOTATIONS_DATA_BRANCH,
            'sha': 'abc',
            'committer': {'name': 'foo', 'email': 'bar'},
            'content': base64.b64encode(json.dumps(annotations, cls=github.AnnotationEncoder).encode()).decode(),
        },
    )(status_code=404)

    with pytest.raises(github.CannotGetBranch):
        github.write_annotations_to_branch(
            github=gh,
            user=github.User(name='foo', email='bar', login='foo'),
            pr_number=123,
            config=config,
            annotations=annotations,
        )


def test_write_annotations_to_branch_annotations_update_forbidden(gh, session, base_config):
    config = base_config(ANNOTATIONS_DATA_BRANCH='annotations', ANNOTATE_MISSING_LINES=True)
    annotations = [
        github.Annotation(
            file=pathlib.Path('file.py'),
            line_start=10,
            line_end=10,
            title='Error',
            message_type='warning',
            message='Error',
        )
    ]
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/branches/{config.ANNOTATIONS_DATA_BRANCH}')(
        json={'protected': False, 'name': config.ANNOTATIONS_DATA_BRANCH}
    )
    session.register(
        'GET', f'/repos/{config.GITHUB_REPOSITORY}/contents/123-annotations.json', params={'ref': 'annotations'}
    )(json={'sha': 'abc'})
    session.register(
        'PUT',
        f'/repos/{config.GITHUB_REPOSITORY}/contents/123-annotations.json',
        json={
            'message': github.COMMIT_MESSAGE,
            'branch': config.ANNOTATIONS_DATA_BRANCH,
            'sha': 'abc',
            'committer': {'name': 'foo', 'email': 'bar'},
            'content': base64.b64encode(json.dumps(annotations, cls=github.AnnotationEncoder).encode()).decode(),
        },
    )(status_code=403)

    with pytest.raises(github.CannotGetBranch):
        github.write_annotations_to_branch(
            github=gh,
            user=github.User(name='foo', email='bar', login='foo'),
            pr_number=123,
            config=config,
            annotations=annotations,
        )


def test_write_annotations_to_branch_annotations_update_conflict(gh, session, base_config):
    config = base_config(ANNOTATIONS_DATA_BRANCH='annotations', ANNOTATE_MISSING_LINES=True)
    annotations = [
        github.Annotation(
            file=pathlib.Path('file.py'),
            line_start=10,
            line_end=10,
            title='Error',
            message_type='warning',
            message='Error',
        )
    ]
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/branches/{config.ANNOTATIONS_DATA_BRANCH}')(
        json={'protected': False, 'name': config.ANNOTATIONS_DATA_BRANCH}
    )
    session.register(
        'GET', f'/repos/{config.GITHUB_REPOSITORY}/contents/123-annotations.json', params={'ref': 'annotations'}
    )(json={'sha': 'abc'})
    session.register(
        'PUT',
        f'/repos/{config.GITHUB_REPOSITORY}/contents/123-annotations.json',
        json={
            'message': github.COMMIT_MESSAGE,
            'branch': config.ANNOTATIONS_DATA_BRANCH,
            'sha': 'abc',
            'committer': {'name': 'foo', 'email': 'bar'},
            'content': base64.b64encode(json.dumps(annotations, cls=github.AnnotationEncoder).encode()).decode(),
        },
    )(status_code=409)

    with pytest.raises(github.CannotGetBranch):
        github.write_annotations_to_branch(
            github=gh,
            user=github.User(name='foo', email='bar', login='foo'),
            pr_number=123,
            config=config,
            annotations=annotations,
        )


def test_write_annotations_to_branch_annotations_update_validation_failed(gh, session, base_config):
    config = base_config(ANNOTATIONS_DATA_BRANCH='annotations', ANNOTATE_MISSING_LINES=True)
    annotations = [
        github.Annotation(
            file=pathlib.Path('file.py'),
            line_start=10,
            line_end=10,
            title='Error',
            message_type='warning',
            message='Error',
        )
    ]
    session.register('GET', f'/repos/{config.GITHUB_REPOSITORY}/branches/{config.ANNOTATIONS_DATA_BRANCH}')(
        json={'protected': False, 'name': config.ANNOTATIONS_DATA_BRANCH}
    )
    session.register(
        'GET', f'/repos/{config.GITHUB_REPOSITORY}/contents/123-annotations.json', params={'ref': 'annotations'}
    )(json={'sha': 'abc'})
    session.register(
        'PUT',
        f'/repos/{config.GITHUB_REPOSITORY}/contents/123-annotations.json',
        json={
            'message': github.COMMIT_MESSAGE,
            'branch': config.ANNOTATIONS_DATA_BRANCH,
            'sha': 'abc',
            'committer': {'name': 'foo', 'email': 'bar'},
            'content': base64.b64encode(json.dumps(annotations, cls=github.AnnotationEncoder).encode()).decode(),
        },
    )(status_code=422)

    with pytest.raises(github.CannotGetBranch):
        github.write_annotations_to_branch(
            github=gh,
            user=github.User(name='foo', email='bar', login='foo'),
            pr_number=123,
            config=config,
            annotations=annotations,
        )
