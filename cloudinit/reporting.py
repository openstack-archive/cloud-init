# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab
"""
cloud-init reporting framework

The reporting framework is intended to allow all parts of cloud-init to
report events in a structured manner.
"""

import abc
import logging

from cloudinit.registry import Registry


FINISH_EVENT_TYPE = 'finish'
START_EVENT_TYPE = 'start'


class ReportingEvent(object):
    """Encapsulation of event formatting."""

    def __init__(self, event_type, name, description):
        self.event_type = event_type
        self.name = name
        self.description = description

    def as_string(self):
        """The event represented as a string."""
        return '{0}: {1}: {2}'.format(
            self.event_type, self.name, self.description)


class FinishReportingEvent(ReportingEvent):

    def __init__(self, name, description, successful=None):
        super(FinishReportingEvent, self).__init__(
            FINISH_EVENT_TYPE, name, description)
        self.successful = successful

    def as_string(self):
        if self.successful is None:
            return super(FinishReportingEvent, self).as_string()
        success_string = 'success' if self.successful else 'fail'
        return '{0}: {1}: {2}: {3}'.format(
            self.event_type, self.name, success_string, self.description)


class ReportingHandler(object):

    @abc.abstractmethod
    def publish_event(self, event):
        raise NotImplementedError


class LogHandler(ReportingHandler):
    """Publishes events to the cloud-init log at the ``INFO`` log level."""

    def publish_event(self, event):
        """Publish an event to the ``INFO`` log level."""
        logger = logging.getLogger(
            '.'.join([__name__, event.event_type, event.name]))
        logger.info(event.as_string())


handler_registry = Registry()
handler_registry.register_item(LogHandler())


def report_event(event):
    """Report an event to all registered event handlers.

    This should generally be called via one of the other functions in
    the reporting module.

    :param event_type:
        The type of the event; this should be a constant from the
        reporting module.
    """
    for handler in handler_registry.registered_items:
        handler.publish_event(event)


def report_finish_event(event_name, event_description, successful=None):
    """Report a "finish" event.

    See :py:func:`.report_event` for parameter details.
    """
    event = FinishReportingEvent(event_name, event_description, successful)
    return report_event(event)


def report_start_event(event_name, event_description):
    """Report a "start" event.

    :param event_name:
        The name of the event; this should be a topic which events would
        share (e.g. it will be the same for start and finish events).

    :param event_description:
        A human-readable description of the event that has occurred.
    """
    event = ReportingEvent(START_EVENT_TYPE, event_name, event_description)
    return report_event(event)
