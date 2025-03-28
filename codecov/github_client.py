from __future__ import annotations

from typing import Any

import httpx

from codecov.exceptions import (
    ApiError,
    ConfigurationException,
    Conflict,
    Forbidden,
    NotFound,
    Unauthorized,
    ValidationFailed,
)
from codecov.log import log

TIMEOUT = 60
BASE_URL = 'https://api.github.com'


class _Executable:
    def __init__(self, _gh: GitHubClient, _method: str, _path: str):
        self._gh = _gh
        self._method = _method
        self._path = _path

    def __call__(self, **kw):
        return self._gh._http(self._method, self._path, **kw)


class _Callable:
    def __init__(self, _gh, _name):
        self._gh = _gh
        self._name = _name

    def __call__(self, *args):
        if len(args) == 0:
            return self
        name = f'{self._name}/{"/".join([str(arg) for arg in args])}'
        return _Callable(self._gh, name)

    def __getattr__(self, attr):
        if attr in ['get', 'put', 'post', 'patch', 'delete']:
            return _Executable(self._gh, attr, self._name)
        name = f'{self._name}/{attr}'
        return _Callable(self._gh, name)


def _response_contents(response: httpx.Response) -> JsonObject | bytes:
    if response.headers.get('content-type', '').startswith('application/json'):
        return response.json(object_hook=JsonObject)
    return response.content


class JsonObject(dict):
    """
    general json object that can bind any fields but also act as a dict.
    """

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as e:
            log.error("'Dict' object has no attribute '%s'", key)
            raise AttributeError from e


class GitHubClient:
    def __init__(self, token: str, url: str = BASE_URL, follow_redirects: bool = True):
        self.token = token
        self.url = url
        self.follow_redirects = follow_redirects
        self.session = self._init_session()

    def _init_session(self) -> httpx.Client:
        log.debug('Creating GitHub client session.')
        session = httpx.Client(
            base_url=self.url,
            follow_redirects=self.follow_redirects,
            headers={'Authorization': f'token {self.token}'},
        )
        if not session:
            log.error(
                'Failed to create GitHub client session. This might be due to an internal configuration or code issue.'
            )
            raise ConfigurationException
        return session

    def __getattr__(self, attr):
        return _Callable(self, f'/{attr}')

    def _http(self, method: str, path: str, *, use_bytes: bool = False, use_text: bool = False, **kw):
        _method = method.lower()
        requests_kwargs: dict[Any, Any] = {}
        headers = kw.pop('headers', {})
        if _method == 'get' and kw:
            requests_kwargs = {'params': kw}

        elif _method in ['post', 'patch', 'put']:
            requests_kwargs = {'json': kw}

        response = self.session.request(
            _method.upper(),
            path,
            timeout=TIMEOUT,
            headers=headers,
            **requests_kwargs,
        )
        contents: str | bytes | JsonObject
        if use_bytes:
            contents = response.content
        elif use_text:
            contents = response.text
        else:
            contents = _response_contents(response)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            exc_cls = ApiError
            match exc.response.status_code:
                case 401:
                    exc_cls = Unauthorized
                case 403:
                    exc_cls = Forbidden
                case 404:
                    exc_cls = NotFound
                case 409:
                    exc_cls = Conflict
                case 422:
                    exc_cls = ValidationFailed
            raise exc_cls(str(contents)) from exc

        return contents
