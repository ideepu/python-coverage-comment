import logging

log = logging.getLogger('codecov')


def setup(debug: bool = False) -> None:
    logging.basicConfig(
        level='DEBUG' if debug else 'INFO',
        format='%(asctime)s.%(msecs)03d %(levelname)s  %(name)s %(module)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )


__all__ = ['log']
