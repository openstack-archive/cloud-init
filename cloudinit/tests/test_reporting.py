# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import unittest

from cloudinit import reporting
from cloudinit.tests.util import mock


class SharedReportEventTestsMixin(object):
    """
    Tests that should hold true for all types of event reporting.
    """

    @property
    def expected_event_type(self):
        raise NotImplementedError

    @property
    def reporting_function(self):
        raise NotImplementedError

    @mock.patch.object(reporting, 'HANDLERS', [])
    @mock.patch('cloudinit.reporting.ReportingEvent')
    def test_report_event_creates_event(self, ReportingEvent):
        event_name, event_description = 'my_test_event', 'my description'
        self.reporting_function()(event_name, event_description)
        self.assertEqual(
            [mock.call(
                self.expected_event_type, event_name, event_description)],
            ReportingEvent.call_args_list)

    @mock.patch('cloudinit.reporting.HANDLERS',
                new_callable=lambda: [mock.MagicMock(), mock.MagicMock()])
    @mock.patch('cloudinit.reporting.ReportingEvent')
    def test_start_event_passes_event_to_defined_handlers(
            self, ReportingEvent, HANDLERS):
        self.reporting_function()('my_test_event', 'my description')
        for handler in HANDLERS:
            self.assertEqual([mock.call(ReportingEvent.return_value)],
                             handler.publish_event.call_args_list)


class TestReportStartEvent(SharedReportEventTestsMixin, unittest.TestCase):
    expected_event_type = reporting.START_EVENT_TYPE
    reporting_function = lambda self: reporting.report_start_event


class TestReportFinishEvent(SharedReportEventTestsMixin, unittest.TestCase):
    expected_event_type = reporting.FINISH_EVENT_TYPE
    reporting_function = lambda self: reporting.report_finish_event


class TestReportingEvent(unittest.TestCase):

    def test_as_string(self):
        event_type, name, description = 'test_type', 'test_name', 'test_desc'
        event = reporting.ReportingEvent(event_type, name, description)
        expected_string_representation = ': '.join(
            [event_type, name, description])
        self.assertEqual(expected_string_representation, event.as_string())


class TestLogHandler(unittest.TestCase):

    @mock.patch.object(reporting.logging, 'getLogger')
    def test_appropriate_logger_used(self, getLogger):
        event_type, event_name = 'test_type', 'test_name'
        event = reporting.ReportingEvent(event_type, event_name, 'description')
        reporting.LogHandler.publish_event(event)
        self.assertEqual(
            [mock.call(
                'cloudinit.reporting.{}.{}'.format(event_type, event_name))],
            getLogger.call_args_list)

    @mock.patch.object(reporting.logging, 'getLogger')
    def test_single_log_message_at_info_published(self, getLogger):
        event = reporting.ReportingEvent('type', 'name', 'description')
        reporting.LogHandler.publish_event(event)
        self.assertEqual(1, getLogger.return_value.info.call_count)

    @mock.patch.object(reporting.logging, 'getLogger')
    def test_log_message_uses_event_as_string(self, getLogger):
        event = reporting.ReportingEvent('type', 'name', 'description')
        reporting.LogHandler.publish_event(event)
        self.assertIn(event.as_string(),
                      getLogger.return_value.info.call_args[0][0])
