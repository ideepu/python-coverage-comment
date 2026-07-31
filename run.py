import sys

from codecov.exceptions import CoreBaseException
from codecov.log import log
from codecov.main import Main


def main_call(name):
    if name == '__main__':
        try:
            Main().run()
        except CoreBaseException as e:
            log.error(f'Error: {str(e)}')
            sys.exit(1)


main_call(name=__name__)
