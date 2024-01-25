# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger('codecov')


def __getattr__(name):
    return getattr(logger, name)
