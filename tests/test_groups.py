import json
import pathlib

import pytest

from codecov.groups import Annotation, AnnotationEncoder, Group, create_missing_coverage_annotations


def test_annotation_str():
    file = pathlib.Path('/path/to/file.py')
    annotation = Annotation(
        file=file, line_start=10, line_end=15, title='Error', message_type='ERROR', message='Something went wrong'
    )
    expected_str = 'ERROR Something went wrong in /path/to/file.py:10-15'
    assert str(annotation) == expected_str


def test_annotation_repr():
    file = pathlib.Path('/path/to/file.py')
    annotation = Annotation(
        file=file, line_start=10, line_end=15, title='Error', message_type='ERROR', message='Something went wrong'
    )
    expected_repr = 'ERROR Something went wrong in /path/to/file.py:10-15'
    assert repr(annotation) == expected_repr


def test_annotation_to_dict():
    file = pathlib.Path('/path/to/file.py')
    annotation = Annotation(
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


def test_annotation_encode():
    file = pathlib.Path('/path/to/file.py')
    annotation = Annotation(
        file=file,
        line_start=10,
        line_end=15,
        title='Error',
        message_type='ERROR',
        message='Something went wrong',
    )
    assert isinstance(Annotation.encode([annotation]), str)


def test_annotation_encoder_annotation():
    encoder = AnnotationEncoder()
    annotation = Annotation(
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
    annotation = Annotation(
        file=pathlib.Path('/path/to/file.py'),
        line_start=10,
        line_end=15,
        title='Error',
        message_type='ERROR',
        message='Something went wrong',
    )
    expected_json = '{"file": "/path/to/file.py", "line_start": 10, "line_end": 15, "title": "Error", "message_type": "ERROR", "message": "Something went wrong"}'
    result = json.dumps(annotation, cls=AnnotationEncoder)
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
        AnnotationEncoder().default(sample)


@pytest.mark.parametrize(
    'annotation_type, annotations, expected_annotations',
    [
        ('error', [], []),
        (
            'error',
            [Group(file=pathlib.Path('file.py'), line_start=10, line_end=10)],
            [
                Annotation(
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
            [Group(file=pathlib.Path('file.py'), line_start=5, line_end=10)],
            [
                Annotation(
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
                Group(file=pathlib.Path('file1.py'), line_start=5, line_end=5),
                Group(file=pathlib.Path('file2.py'), line_start=10, line_end=15),
            ],
            [
                Annotation(
                    file=pathlib.Path('file1.py'),
                    line_start=5,
                    line_end=5,
                    title='Missing coverage',
                    message_type='notice',
                    message='Missing coverage on line 5',
                ),
                Annotation(
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
    assert create_missing_coverage_annotations(annotation_type, annotations) == expected_annotations
