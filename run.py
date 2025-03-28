# -*- coding: utf-8 -*-
from codecov.main import Main


def main_call(name):
    if name == '__main__':
        Main().run()


main_call(name=__name__)
