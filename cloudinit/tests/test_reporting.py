# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import unittest

from cloudinit import reporting
from cloudinit.test import TestCase
from cloudinit.tests.util import mock


class TestReportStartEvent(unittest.TestCase):

    @mock.patch('cloudinit.reporting.HANDLERS',
                new_callable=lambda: [mock.MagicMock(), mock.MagicMock()])
    def test_report_start_event_passes_something_with_as_string_to_handlers(
            self, HANDLERS):
        event_name, event_description = 'my_test_event', 'my description'
        reporting.report_start_event(event_name, event_description)
        expected_string_representation = ': '.join(
            ['start', event_name, event_description])
        for handler in HANDLERS:
            self.assertEqual(1, handler.publish_event.call_count)
            event = handler.publish_event.call_args[0][0]
            self.assertEqual(expected_string_representation, event.as_string())


class TestReportFinishEvent(unittest.TestCase):

    def _report_finish_event(self, successful=None):
        event_name, event_description = 'my_test_event', 'my description'
        reporting.report_finish_event(
            event_name, event_description, successful=successful)
        return event_name, event_description

    def assertHandlersPassedObjectWithAsString(
            self, handlers, expected_as_string):
        for handler in handlers:
            self.assertEqual(1, handler.publish_event.call_count)
            event = handler.publish_event.call_args[0][0]
            self.assertEqual(expected_as_string, event.as_string())

    @mock.patch('cloudinit.reporting.HANDLERS',
                new_callable=lambda: [mock.MagicMock(), mock.MagicMock()])
    def test_report_finish_event_passes_something_with_as_string_to_handlers(
            self, HANDLERS):
        event_name, event_description = self._report_finish_event()
        expected_string_representation = ': '.join(
            ['finish', event_name, event_description])
        self.assertHandlersPassedObjectWithAsString(
            HANDLERS, expected_string_representation)

    @mock.patch('cloudinit.reporting.HANDLERS',
                new_callable=lambda: [mock.MagicMock(), mock.MagicMock()])
    def test_reporting_successful_finish_has_sensible_string_repr(self,
                                                                  HANDLERS):
        event_name, event_description = self._report_finish_event(
            successful=True)
        expected_string_representation = ': '.join(
            ['finish', event_name, 'success', event_description])
        self.assertHandlersPassedObjectWithAsString(
            HANDLERS, expected_string_representation)

    @mock.patch('cloudinit.reporting.HANDLERS',
                new_callable=lambda: [mock.MagicMock(), mock.MagicMock()])
    def test_reporting_unsuccessful_finish_has_sensible_string_repr(self,
                                                                    HANDLERS):
        event_name, event_description = self._report_finish_event(
            successful=False)
        expected_string_representation = ': '.join(
            ['finish', event_name, 'fail', event_description])
        self.assertHandlersPassedObjectWithAsString(
            HANDLERS, expected_string_representation)


class TestReportingEvent(unittest.TestCase):

    def test_as_string(self):
        event_type, name, description = 'test_type', 'test_name', 'test_desc'
        event = reporting.ReportingEvent(event_type, name, description)
        expected_string_representation = ': '.join(
            [event_type, name, description])
        self.assertEqual(expected_string_representation, event.as_string())


class TestLogHandler(TestCase):

    @mock.patch.object(reporting.logging, 'getLogger')
    def test_appropriate_logger_used(self, getLogger):
        event_type, event_name = 'test_type', 'test_name'
        event = reporting.ReportingEvent(event_type, event_name, 'description')
        reporting.LogHandler.publish_event(event)
        self.assertEqual(
            [mock.call(
                'cloudinit.reporting.{0}.{1}'.format(event_type, event_name))],
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
