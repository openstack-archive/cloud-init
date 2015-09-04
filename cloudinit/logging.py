# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

from __future__ import absolute_import

import logging
import sys

_BASE = __name__.split(".", 1)[0]

# Add a BLATHER level, this matches the multiprocessing utils.py module (and
# kazoo and others) that declares a similar level, this level is for
# information that is even lower level than regular DEBUG and gives out so
# much runtime information that it is only useful by low-level/certain users...
BLATHER = 5

# Copy over *select* attributes to make it easy to use this module.
CRITICAL = logging.CRITICAL
DEBUG = logging.DEBUG
ERROR = logging.ERROR
FATAL = logging.FATAL
INFO = logging.INFO
NOTSET = logging.NOTSET
WARN = logging.WARN
WARNING = logging.WARNING


class _BlatherLoggerAdapter(logging.LoggerAdapter):

    def blather(self, msg, *args, **kwargs):
        """Delegate a blather call to the underlying logger."""
        self.log(BLATHER, msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        """Delegate a warning call to the underlying logger."""
        self.warning(msg, *args, **kwargs)


# TODO(harlowja): we should remove when we no longer have to support 2.6...
if sys.version_info[0:2] == (2, 6):  # pragma: nocover
    from logutils.dictconfig import dictConfig

    class _FixedBlatherLoggerAdapter(_BlatherLoggerAdapter):
        """Ensures isEnabledFor() exists on adapters that are created."""

        def isEnabledFor(self, level):
            return self.logger.isEnabledFor(level)

    _BlatherLoggerAdapter = _FixedBlatherLoggerAdapter

    # Taken from python2.7 (same in python3.4)...
    class _NullHandler(logging.Handler):
        """This handler does nothing.

        It's intended to be used to avoid the
        "No handlers could be found for logger XXX" one-off warning. This is
        important for library code, which may contain code to log events. If a
        user of the library does not configure logging, the one-off warning
        might be produced; to avoid this, the library developer simply needs
        to instantiate a _NullHandler and add it to the top-level logger of the
        library module or package.
        """

        def handle(self, record):
            """Stub."""

        def emit(self, record):
            """Stub."""

        def createLock(self):
            self.lock = None

else:
    from logging.config import dictConfig
    _NullHandler = logging.NullHandler


def getLogger(name=_BASE, extra=None):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(_NullHandler())
    return _BlatherLoggerAdapter(logger, extra=extra)


def configure_logging(log_to_console=False):
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
            },
        },
        'loggers': {
            '': {
                'handlers': [],
                'level': 'DEBUG',
                'propagate': True,
            },
        },
    }
    if log_to_console:
        logging_config['loggers']['']['handlers'].append('console')
    dictConfig(logging_config)
