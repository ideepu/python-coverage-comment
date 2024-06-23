# -*- coding: utf-8 -*-
from __future__ import annotations

import dataclasses
import decimal
import inspect
import pathlib
from collections.abc import MutableMapping
from typing import Any


class MissingEnvironmentVariable(Exception):
    pass


class InvalidAnnotationType(Exception):
    pass


def path_below(path_str: str | pathlib.Path) -> pathlib.Path:
    path = pathlib.Path(path_str).resolve()
    if not (path.exists() and path.is_file()):
        raise ValueError('Path does not exist')

    if path.suffix != '.json':
        raise ValueError('The file is not a JSON file.')
    return path


def str_to_bool(value: str) -> bool:
    return value.lower() in ('1', 'true', 'yes')


# pylint: disable=invalid-name, too-many-instance-attributes
@dataclasses.dataclass
class Config:
    """This object defines the environment variables"""

    GITHUB_REPOSITORY: str
    COVERAGE_PATH: pathlib.Path
    GITHUB_TOKEN: str = dataclasses.field(repr=False)
    GITHUB_PR_NUMBER: int | None = None
    # Branch to run the action on (alternate to get PR number if not provided)
    # Example Organisation:branch-name (Company:sample-branch) or User:branch-name (user:sample-branch)
    GITHUB_REF: str | None = None
    GITHUB_BASE_REF: str = 'main'
    SUBPROJECT_ID: str | None = None
    MINIMUM_GREEN: decimal.Decimal = decimal.Decimal('100')
    MINIMUM_ORANGE: decimal.Decimal = decimal.Decimal('70')
    BRANCH_COVERAGE: bool = False
    SKIP_COVERAGE: bool = False
    ANNOTATE_MISSING_LINES: bool = False
    ANNOTATION_TYPE: str = 'warning'
    ANNOTATIONS_OUTPUT_PATH: pathlib.Path | None = None
    ANNOTATIONS_DATA_BRANCH: str | None = None
    MAX_FILES_IN_COMMENT: int = 25
    COMPLETE_PROJECT_REPORT: bool = False
    COVERAGE_REPORT_URL: str | None = None
    # Only for debugging, not exposed in the action
    DEBUG: bool = False

    def __post_init__(self) -> None:
        if self.GITHUB_PR_NUMBER is None and self.GITHUB_REF is None:
            raise ValueError('Either GITHUB_PR_NUMBER or GITHUB_REF must be provided')

    # Clean methods
    @classmethod
    def clean_minimum_green(cls, value: str) -> decimal.Decimal:
        return decimal.Decimal(value)

    @classmethod
    def clean_minimum_orange(cls, value: str) -> decimal.Decimal:
        return decimal.Decimal(value)

    @classmethod
    def clean_annotate_missing_lines(cls, value: str) -> bool:
        return str_to_bool(value)

    @classmethod
    def clean_skip_coverage(cls, value: str) -> bool:
        return str_to_bool(value)

    @classmethod
    def clean_branch_coverage(cls, value: str) -> bool:
        return str_to_bool(value)

    @classmethod
    def clean_complete_project_report(cls, value: str) -> bool:
        return str_to_bool(value)

    @classmethod
    def clean_debug(cls, value: str) -> bool:
        return str_to_bool(value)

    @classmethod
    def clean_annotation_type(cls, value: str) -> str:
        if value not in {'notice', 'warning', 'error'}:
            raise InvalidAnnotationType(
                f'The annotation type {value} is not valid. Please choose from notice, warning or error'
            )
        return value

    @classmethod
    def clean_github_pr_number(cls, value: str) -> int:
        return int(value)

    @classmethod
    def clean_coverage_path(cls, value: str) -> pathlib.Path:
        return path_below(value)

    @classmethod
    def clean_annotations_output_path(cls, value: str) -> pathlib.Path:
        return pathlib.Path(value)

    # We need to type environ as a MutableMapping because that's what
    # os.environ is, and `dict[str, str]` is not enough
    @classmethod
    def from_environ(cls, environ: MutableMapping[str, str]) -> Config:
        possible_variables = list(inspect.signature(cls).parameters)
        config: dict[str, Any] = {k: v for k, v in environ.items() if k in possible_variables}
        for key, value in list(config.items()):
            if func := getattr(cls, f'clean_{key.lower()}', None):
                try:
                    config[key] = func(value)
                except ValueError as exc:
                    raise ValueError(f'{key}: {exc!s}') from exc

        try:
            config_obj = cls(**config)
        except TypeError as e:
            missing = {
                name
                for name, param in inspect.signature(cls).parameters.items()
                if param.default is inspect.Parameter.empty
            } - set(environ)
            raise MissingEnvironmentVariable(f" missing environment variable(s): {', '.join(missing)}") from e
        return config_obj
