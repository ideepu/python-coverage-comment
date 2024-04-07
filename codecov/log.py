# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger('codecov')


def __getattr__(name):
    return getattr(logger, name)


def setup(debug: bool = False):
    logging.basicConfig(
        level='DEBUG' if debug else 'INFO',
        format='%(asctime)s.%(msecs)03d %(levelname)s  %(name)s %(module)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
