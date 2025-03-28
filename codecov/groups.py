# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import dataclasses
import functools
import itertools
import json
import pathlib
from collections.abc import Iterable
from typing import Self


@dataclasses.dataclass(frozen=True)
class Group:
    file: pathlib.Path
    line_start: int
    line_end: int


class AnnotationEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Annotation):
            return o.to_dict()
        return super().default(o)


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

    @classmethod
    def encode(cls, annotations: list[Self]) -> str:
        return base64.b64encode(json.dumps(annotations, cls=AnnotationEncoder).encode()).decode()


def create_missing_coverage_annotations(
    annotation_type: str,
    annotations: Iterable[Group],
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


# TODO: Write tests for this function
def compute_contiguous_groups(
    values: list[int],
    separators: set[int],
    joiners: set[int],
    max_gap: int,
) -> list[tuple[int, int]]:
    """
    Given a list of (sorted) values, a list of separators and a list of
    joiners, return a list of ranges (start, included end) describing groups of
    values.

    Groups are created by joining contiguous values together, and in some cases
    by merging groups, enclosing a gap of values between them. Gaps that may be
    enclosed are small gaps (<= max_gap values after removing all joiners)
    where no line is a "separator"
    """
    contiguous_groups: list[tuple[int, int]] = []
    for _, contiguous_group in itertools.groupby(zip(values, itertools.count(1)), lambda x: x[1] - x[0]):
        grouped_values = (e[0] for e in contiguous_group)
        first = next(grouped_values)
        try:
            *_, last = grouped_values
        except ValueError:
            last = first
        contiguous_groups.append((first, last))

    def reducer(acc: list[tuple[int, int]], group: tuple[int, int]) -> list[tuple[int, int]]:
        if not acc:
            return [group]

        last_group = acc[-1]
        last_start, last_end = last_group
        next_start, next_end = group

        gap = set(range(last_end + 1, next_start)) - joiners

        gap_is_small = len(gap) <= max_gap
        gap_contains_separators = gap & separators

        if gap_is_small and not gap_contains_separators:
            acc[-1] = (last_start, next_end)
            return acc

        acc.append(group)
        return acc

    return functools.reduce(reducer, contiguous_groups, [])
