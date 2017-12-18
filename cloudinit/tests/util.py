# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import logging
import sys

try:
    from unittest import mock
except ImportError:
    import mock  # noqa


_IS_PY26 = sys.version_info[0:2] == (2, 6)


# This is similar with unittest.TestCase.assertLogs from Python 3.4.
class SnatchHandler(logging.Handler):

    if _IS_PY26:
        # Old style junk is required on 2.6...
        def __init__(self, *args, **kwargs):
            logging.Handler.__init__(self, *args, **kwargs)
            self.output = []
    else:
        def __init__(self, *args, **kwargs):
            super(SnatchHandler, self).__init__(*args, **kwargs)
            self.output = []

    def emit(self, record):
        msg = self.format(record)
        self.output.append(msg)


class LogSnatcher(object):
    """A context manager to capture emitted logged messages.

    The class can be used as following::

        with LogSnatcher('plugins.windows.createuser') as snatcher:
            LOG.info("doing stuff")
            LOG.info("doing stuff %s", 1)
            LOG.warning("doing other stuff")
            ...
        self.assertEqual(snatcher.output,
                         ['INFO:unknown:doing stuff',
                          'INFO:unknown:doing stuff 1',
                          'WARN:unknown:doing other stuff'])
    """

    @property
    def output(self):
        """Get the output of this Snatcher.

        The output is a list of log messages, already formatted.
        """
        return self._snatch_handler.output

    def __init__(self, logger_name):
        self._logger_name = logger_name
        self._snatch_handler = SnatchHandler()
        self._logger = logging.getLogger(self._logger_name)
        self._previous_level = self._logger.getEffectiveLevel()

    def __enter__(self):
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers.append(self._snatch_handler)
        return self

    def __exit__(self, *args):
        self._logger.handlers.remove(self._snatch_handler)
        self._logger.setLevel(self._previous_level)
