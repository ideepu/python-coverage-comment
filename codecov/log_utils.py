# -*- coding: utf-8 -*-
import logging


class ConsoleFormatter(logging.Formatter):
    def format(self, record) -> str:
        log = super().format(record)

        return f'{int(record.created)} {record.levelname} {record.name} - {log}'
