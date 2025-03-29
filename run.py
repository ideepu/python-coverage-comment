import sys

from codecov.exceptions import CoreBaseException
from codecov.main import Main


def main_call(name):
    if name == '__main__':
        try:
            Main().run()
        except CoreBaseException:
            sys.exit(1)


main_call(name=__name__)
