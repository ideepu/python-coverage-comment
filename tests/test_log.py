# -*- coding: utf-8 -*-
from unittest.mock import patch

from codecov import log


def test_setup_debug():
    with patch('logging.basicConfig') as mock_basic_config:
        log.setup(debug=True)
        mock_basic_config.assert_called_once_with(
            level='DEBUG',
            format='%(asctime)s.%(msecs)03d %(levelname)s  %(name)s %(module)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )


def test_setup_not_debug():
    with patch('logging.basicConfig') as mock_basic_config:
        log.setup(debug=False)
        mock_basic_config.assert_called_once_with(
            level='INFO',
            format='%(asctime)s.%(msecs)03d %(levelname)s  %(name)s %(module)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )
