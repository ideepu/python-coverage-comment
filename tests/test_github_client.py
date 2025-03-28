# -*- coding: utf-8 -*-
from __future__ import annotations

import secrets
from unittest.mock import patch

import pytest

from codecov.exceptions import ApiError, ConfigurationException
from codecov.github_client import GitHubClient, JsonObject


def test_github_client_init():
    with pytest.raises(ConfigurationException):
        with patch('httpx.Client', return_value=None):
            GitHubClient(token=secrets.token_hex(16))


def test_github_client_get(session, gh_client):
    session.register('GET', '/repos/a/b/issues', timeout=60, params={'a': 1})(json={'foo': 'bar'})

    assert gh_client.repos('a/b').issues().get(a=1) == {'foo': 'bar'}


def test_github_client_get_text(session, gh_client):
    session.register('GET', '/repos/a/b/issues', timeout=60, params={'a': 1})(
        text='foobar',
        headers={'content-type': 'application/vnd.github.raw+json'},
    )

    assert gh_client.repos('a/b').issues().get(a=1, use_text=True) == 'foobar'


def test_github_client_get_bytes(session, gh_client):
    session.register('GET', '/repos/a/b/issues', timeout=60, params={'a': 1})(
        text='foobar',
        headers={'content-type': 'application/vnd.github.raw+json'},
    )

    assert gh_client.repos('a/b').issues().get(a=1, use_bytes=True) == b'foobar'


def test_github_client_get_headers(session, gh_client):
    session.register('GET', '/repos/a/b/issues', timeout=60, params={'a': 1})(
        json={'foo': 'bar'},
        headers={'X-foo': 'yay'},
    )

    assert gh_client.repos('a/b').issues().get(a=1, headers={'X-foo': 'yay'}) == {'foo': 'bar'}


def test_github_client_post_non_json(session, gh_client):
    session.register('POST', '/repos/a/b/issues', timeout=60, json={'a': 1})()

    gh_client.repos('a/b').issues().post(a=1)


def test_json_object():
    obj = JsonObject({'a': 1})

    assert obj.a == 1


def test_json_object_error():
    obj = JsonObject({'a': 1})

    with pytest.raises(AttributeError):
        _ = obj.b


def test_github_client_get_error(session, gh_client):
    session.register('GET', '/repos')(
        json={'foo': 'bar'},
        status_code=404,
    )

    with pytest.raises(ApiError) as exc_info:
        gh_client.repos.get()

    assert str(exc_info.value) == "{'foo': 'bar'}"


def test_github_client_get_error_non_json(session, gh_client):
    session.register('GET', '/repos')(
        text='{foobar',
        headers={'content-type': 'text/plain'},
        status_code=404,
    )

    with pytest.raises(ApiError) as exc_info:
        gh_client.repos.get()

    assert str(exc_info.value) == "b'{foobar'"
