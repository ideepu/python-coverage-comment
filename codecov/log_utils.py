# -*- coding: utf-8 -*-
import logging

from codecov import github

LEVEL_MAPPING = {
    50: 'error',
    40: 'error',
    30: 'warning',
    20: 'notice',
    10: 'debug',
}


class ConsoleFormatter(logging.Formatter):
    def format(self, record) -> str:
        log = super().format(record)

        return f'{int(record.created)} {record.levelname} {record.name} - {log}'


class GitHubFormatter(logging.Formatter):
    def format(self, record) -> str:
        log = super().format(record)
        level = LEVEL_MAPPING[record.levelno]

        return github.get_workflow_command(command=level, command_value=log)
