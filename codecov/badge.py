"""
This module should contain only the things relevant to the badge being computed
by shields.io
"""

import decimal
import urllib.parse

from codecov.log import log


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
        log.error('Both "color" and "message" are required to generate the badge URL.')
        raise ValueError

    code = '-'.join(e.replace('_', '__').replace('-', '--') for e in (label, message, color) if e)
    # Please read here on how this badge creation works https://shields.io/badges
    return 'https://img.shields.io/badge/' + urllib.parse.quote(f'{code}.svg')
