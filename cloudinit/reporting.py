# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab
"""
cloud-init reporting framework

The reporting framework is intended to allow all parts of cloud-init to
report events in a structured manner.
"""

import logging


FINISH_EVENT_TYPE = 'finish'
START_EVENT_TYPE = 'start'


class ReportingEvent(object):
    """
    Encapsulation of event formatting.
    """

    def __init__(self, event_type, name, description):
        self.event_type = event_type
        self.name = name
        self.description = description

    def as_string(self):
        """
        The event represented as a string.
        """
        return '{}: {}: {}'.format(
            self.event_type, self.name, self.description)


class LogHandler(object):
    """
    Publishes events to the cloud-init log at the ``INFO`` log level.
    """

    @staticmethod
    def publish_event(event):
        """
        Publish an event to the ``INFO`` log level.
        """
        logger = logging.getLogger(
            '.'.join([__name__, event.event_type, event.name]))
        logger.info(event.as_string())


HANDLERS = [LogHandler]


def report_event(event_type, event_name, event_description):
    """
    Report an event to all registered event handlers.

    This should generally be called via one of the other functions in
    the reporting module.

    :param event_type:
        The type of the event; this should be a constant from the
        reporting module.

    :param event_name:
        The name of the event; this should be a topic which events would
        share (e.g. it will be the same for start and finish events).

    :param event_description:
        A human-readable description of the event that has occurred.
    """
    event = ReportingEvent(event_type, event_name, event_description)
    for handler in HANDLERS:
        handler.publish_event(event)


def report_finish_event(*args):
    """
    Report a "finish" event.

    See :py:func:`.report_event` for parameter details.
    """
    return report_event(FINISH_EVENT_TYPE, *args)


def report_start_event(*args):
    """
    Report a "start" event.

    See :py:func:`.report_event` for parameter details.
    """
    return report_event(START_EVENT_TYPE, *args)
