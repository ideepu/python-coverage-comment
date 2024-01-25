# -*- coding: utf-8 -*-
from __future__ import annotations

import decimal

import pytest

from codecov import badge


@pytest.mark.parametrize(
    'rate, expected',
    [
        (decimal.Decimal('10'), 'red'),
        (decimal.Decimal('80'), 'orange'),
        (decimal.Decimal('99'), 'brightgreen'),
    ],
)
def test_get_badge_color(rate, expected):
    color = badge.get_badge_color(
        rate=rate,
        minimum_green=decimal.Decimal('90'),
        minimum_orange=decimal.Decimal('60'),
    )
    assert color == expected


def test_get_static_badge_url():
    result = badge.get_static_badge_url(label='a-b', message='c_d e', color='green')

    assert result == 'https://img.shields.io/badge/a--b-c__d%20e-green.svg'


@pytest.mark.parametrize(
    'label, message, color',
    [
        (
            'Label',
            '',
            'brightgreen',
        ),
        (
            'Label',
            '100% > 99%',
            '',
        ),
    ],
)
def test_get_static_badge_url__error(label, message, color):
    with pytest.raises(ValueError):
        badge.get_static_badge_url(label=label, message=message, color=color)
