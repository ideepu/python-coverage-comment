from __future__ import annotations

import dataclasses
import decimal
import functools
import hashlib
import itertools
import pathlib
from importlib import resources

import jinja2
from jinja2.sandbox import SandboxedEnvironment

from codecov import badge, diff_grouper
from codecov.coverage import Coverage, DiffCoverage, FileCoverage, FileDiffCoverage
from codecov.exceptions import MissingMarker, TemplateException
from codecov.log import log

MARKER = """<!-- This comment was generated by CI codecov{id_part} -->"""


def get_marker(marker_id: str | None):
    return MARKER.format(id_part=f' (id: {marker_id})' if marker_id else '')


def pluralize(number, singular='', plural='s'):
    if number == 1:
        return singular

    return plural


def remove_exponent(val: decimal.Decimal) -> decimal.Decimal:
    # From https://docs.python.org/3/library/decimal.html#decimal-faq
    return val.quantize(decimal.Decimal(1)) if val == val.to_integral() else val.normalize()


def percentage_value(val: decimal.Decimal, precision: int = 2) -> decimal.Decimal:
    return remove_exponent(
        (decimal.Decimal('100') * val).quantize(
            decimal.Decimal('1.' + ('0' * precision)),
            rounding=decimal.ROUND_DOWN,
        )
    )


def pct(val: decimal.Decimal, precision: int = 2) -> str:
    rounded = percentage_value(val=val, precision=precision)
    return f'{rounded:f}%'


def x100(val: decimal.Decimal):
    return val * 100


@dataclasses.dataclass
class FileInfo:
    path: pathlib.Path
    coverage: FileCoverage
    diff: FileDiffCoverage | None


def get_comment_markdown(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    coverage: Coverage,
    diff_coverage: DiffCoverage,
    files: list[FileInfo],
    count_files: int,
    coverage_files: list[FileInfo],
    count_coverage_files: int,
    max_files: int | None,
    minimum_green: decimal.Decimal,
    minimum_orange: decimal.Decimal,
    repo_name: str,
    pr_number: int,
    base_ref: str,
    base_template: str,
    marker: str,
    subproject_id: str | None = None,
    branch_coverage: bool = False,
    complete_project_report: bool = False,
    coverage_report_url: str | None = None,
):
    env = SandboxedEnvironment(loader=jinja2.FileSystemLoader('codecov/template_files/'))
    env.filters['pct'] = pct
    env.filters['x100'] = x100
    env.filters['generate_badge'] = badge.get_static_badge_url
    env.filters['pluralize'] = pluralize
    env.filters['file_url'] = functools.partial(
        get_file_url, repo_name=repo_name, pr_number=pr_number, base_ref=base_ref
    )
    env.filters['get_badge_color'] = functools.partial(
        badge.get_badge_color,
        minimum_green=minimum_green,
        minimum_orange=minimum_orange,
    )

    missing_diff_lines = {
        key: list(value)
        for key, value in itertools.groupby(
            diff_grouper.get_diff_missing_groups(coverage=coverage, diff_coverage=diff_coverage),
            lambda x: x.file,
        )
    }

    missing_lines_for_whole_project = {
        key: list(value)
        for key, value in itertools.groupby(
            diff_grouper.get_missing_groups(coverage=coverage),
            lambda x: x.file,
        )
    }
    try:
        comment = env.from_string(base_template).render(
            coverage=coverage,
            diff_coverage=diff_coverage,
            max_files=max_files,
            files=files,
            count_files=count_files,
            coverage_files=coverage_files,
            count_coverage_files=count_coverage_files,
            missing_diff_lines=missing_diff_lines,
            missing_lines_for_whole_project=missing_lines_for_whole_project,
            subproject_id=subproject_id,
            marker=marker,
            branch_coverage=branch_coverage,
            complete_project_report=complete_project_report,
            coverage_report_url=coverage_report_url,
        )
    except jinja2.exceptions.TemplateError as exc:
        log.error('Error rendering template: %s', exc)
        raise TemplateException from exc

    if marker not in comment:
        log.error('Marker not found in the comment template')
        raise MissingMarker

    return comment


def select_changed_files(
    *,
    coverage: Coverage,
    diff_coverage: DiffCoverage,
    max_files: int | None,
) -> tuple[list[FileInfo], int, list[FileInfo]]:
    """
    Selects the MAX_FILES files with the most new missing lines sorted by path
    These are the files which have been modified in the PR

    """

    files = []
    for path, coverage_file in coverage.files.items():
        diff_coverage_file = diff_coverage.files.get(path)

        file_info = FileInfo(
            path=path,
            coverage=coverage_file,
            diff=diff_coverage_file,
        )
        has_diff = bool(diff_coverage_file and diff_coverage_file.added_statements)

        if has_diff:
            files.append(file_info)

    return sort_and_trucate_files(files=files, max_files=max_files), len(files), files


def select_files(
    *,
    coverage: Coverage,
    changed_files_info: list[FileInfo],
    max_files: int | None,
) -> tuple[list[FileInfo], int]:
    """
    Selects the no of `max_files` files from the whole project coverage
    Selects only files which are not in changed files report
    Select only files which have statements (not empty files)
    """

    files = []
    changed_files_path = {file.path for file in changed_files_info}
    for path, coverage_file in coverage.files.items():
        # Don't show the report for files that have been modified in the PR
        # This is gonne be covered in the changed files report
        if path in changed_files_path:
            continue

        # Don't show the report for files that have no statements
        if coverage_file.info.num_statements == 0:
            continue

        file_info = FileInfo(path=path, coverage=coverage_file, diff=None)
        files.append(file_info)

    return sort_and_trucate_files(files=files, max_files=max_files), len(files)


def sort_and_trucate_files(files: list[FileInfo], max_files: int | None) -> list[FileInfo]:
    files = sorted(files, key=sort_order, reverse=True)
    if max_files is not None:
        files = files[:max_files]
    return sorted(files, key=lambda x: x.path)


def sort_order(file_info: FileInfo) -> tuple[int, int, int]:
    """
    Sort order for files:
    1. Files with the most new missing lines
    2. Files with the most added lines (from the diff)
    3. Files with the most new executed lines (including not in the diff)
    """
    new_missing_lines = len(file_info.coverage.missing_lines)
    added_statements = len(file_info.diff.added_statements) if file_info.diff else 0
    new_covered_lines = len(file_info.coverage.executed_lines)

    return abs(new_missing_lines), added_statements, abs(new_covered_lines)


def read_template_file(template: str) -> str:
    return (resources.files('codecov') / 'template_files' / template).read_text()


def get_file_url(  # pylint: disable=too-many-arguments
    filename: pathlib.Path,
    lines: tuple[int, int] | None = None,
    base: bool = False,
    *,
    repo_name: str,
    pr_number: int,
    base_ref: str,
) -> str:
    if base:
        s = f'https://github.com/{repo_name}/blob/{base_ref}/{str(filename)}'
        if lines is not None:
            s += f'#L{lines[0]}-L{lines[1]}'
        return s

    # To link to a file in a PR, GitHub uses the link to the file overview combined with a SHA256 hash of the file path
    s = f"https://github.com/{repo_name}/pull/{pr_number}/files#diff-{hashlib.sha256(str(filename).encode('utf-8')).hexdigest()}"

    if lines is not None:
        # R stands for Right side of the diff. But since we generate these links for new code we only need the right side.
        s += f'R{lines[0]}-R{lines[1]}'

    return s
