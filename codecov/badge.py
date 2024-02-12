# -*- coding: utf-8 -*-
"""
This module should contain only the things relevant to the badge being computed
by shields.io
"""
from __future__ import annotations

import decimal
import urllib.parse


def get_badge_color(
    rate: decimal.Decimal,
    minimum_green: decimal.Decimal,
    minimum_orange: decimal.Decimal,
) -> str:
    if rate >= minimum_green:
        return 'brightgreen'

    if rate >= minimum_orange:
        return 'orange'

    return 'red'


def get_static_badge_url(label: str, message: str, color: str) -> str:
    if not color or not message:
        raise ValueError('color and message are required')
    code = '-'.join(e.replace('_', '__').replace('-', '--') for e in (label, message, color) if e)
    return 'https://img.shields.io/badge/' + urllib.parse.quote(f'{code}.svg')
