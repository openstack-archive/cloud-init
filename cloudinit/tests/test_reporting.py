# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

from cloudinit import reporting
from cloudinit.tests import TestCase
from cloudinit.tests.util import mock


def _fake_registry():
    return mock.Mock(registered_items={'a': mock.MagicMock(),
                                       'b': mock.MagicMock()})


class TestReportStartEvent(TestCase):

    @mock.patch('cloudinit.reporting.instantiated_handler_registry',
                new_callable=_fake_registry)
    def test_report_start_event_passes_something_with_as_string_to_handlers(
            self, instantiated_handler_registry):
        event_name, event_description = 'my_test_event', 'my description'
        reporting.report_start_event(event_name, event_description)
        expected_string_representation = ': '.join(
            ['start', event_name, event_description])
        for _, handler in (
                instantiated_handler_registry.registered_items.items()):
            self.assertEqual(1, handler.publish_event.call_count)
            event = handler.publish_event.call_args[0][0]
            self.assertEqual(expected_string_representation, event.as_string())


class TestReportFinishEvent(TestCase):

    def _report_finish_event(self, result=reporting.status.SUCCESS):
        event_name, event_description = 'my_test_event', 'my description'
        reporting.report_finish_event(
            event_name, event_description, result=result)
        return event_name, event_description

    def assertHandlersPassedObjectWithAsString(
            self, handlers, expected_as_string):
        for _, handler in handlers.items():
            self.assertEqual(1, handler.publish_event.call_count)
            event = handler.publish_event.call_args[0][0]
            self.assertEqual(expected_as_string, event.as_string())

    @mock.patch('cloudinit.reporting.instantiated_handler_registry',
                new_callable=_fake_registry)
    def test_report_finish_event_passes_something_with_as_string_to_handlers(
            self, instantiated_handler_registry):
        event_name, event_description = self._report_finish_event()
        expected_string_representation = ': '.join(
            ['finish', event_name, reporting.status.SUCCESS,
             event_description])
        self.assertHandlersPassedObjectWithAsString(
            instantiated_handler_registry.registered_items,
            expected_string_representation)

    @mock.patch('cloudinit.reporting.instantiated_handler_registry',
                new_callable=_fake_registry)
    def test_reporting_successful_finish_has_sensible_string_repr(
            self, instantiated_handler_registry):
        event_name, event_description = self._report_finish_event(
            result=reporting.status.SUCCESS)
        expected_string_representation = ': '.join(
            ['finish', event_name, reporting.status.SUCCESS,
             event_description])
        self.assertHandlersPassedObjectWithAsString(
            instantiated_handler_registry.registered_items,
            expected_string_representation)

    @mock.patch('cloudinit.reporting.instantiated_handler_registry',
                new_callable=_fake_registry)
    def test_reporting_unsuccessful_finish_has_sensible_string_repr(
            self, instantiated_handler_registry):
        event_name, event_description = self._report_finish_event(
            result=reporting.status.FAIL)
        expected_string_representation = ': '.join(
            ['finish', event_name, reporting.status.FAIL, event_description])
        self.assertHandlersPassedObjectWithAsString(
            instantiated_handler_registry.registered_items,
            expected_string_representation)


class TestReportingEvent(TestCase):

    def test_as_string(self):
        event_type, name, description = 'test_type', 'test_name', 'test_desc'
        event = reporting.ReportingEvent(event_type, name, description)
        expected_string_representation = ': '.join(
            [event_type, name, description])
        self.assertEqual(expected_string_representation, event.as_string())


class TestReportingHandler(TestCase):

    def test_no_default_publish_event_implementation(self):
        self.assertRaises(NotImplementedError,
                          reporting.handlers.ReportingHandler().publish_event,
                          None)


class TestLogHandler(TestCase):

    @mock.patch.object(reporting.handlers.logging, 'getLogger')
    def test_appropriate_logger_used(self, getLogger):
        event_type, event_name = 'test_type', 'test_name'
        event = reporting.ReportingEvent(event_type, event_name, 'description')
        reporting.handlers.LogHandler().publish_event(event)
        self.assertEqual(
            [mock.call(
                'cloudinit.reporting.{0}.{1}'.format(event_type, event_name))],
            getLogger.call_args_list)

    @mock.patch.object(reporting.handlers.logging, 'getLogger')
    def test_single_log_message_at_info_published(self, getLogger):
        event = reporting.ReportingEvent('type', 'name', 'description')
        reporting.handlers.LogHandler().publish_event(event)
        self.assertEqual(1, getLogger.return_value.info.call_count)

    @mock.patch.object(reporting.handlers.logging, 'getLogger')
    def test_log_message_uses_event_as_string(self, getLogger):
        event = reporting.ReportingEvent('type', 'name', 'description')
        reporting.handlers.LogHandler().publish_event(event)
        self.assertIn(event.as_string(),
                      getLogger.return_value.info.call_args[0][0])


class TestDefaultRegisteredHandler(TestCase):

    def test_log_handler_registered_by_default(self):
        registered_items = (
            reporting.instantiated_handler_registry.registered_items)
        for _, item in registered_items.items():
            if isinstance(item, reporting.handlers.LogHandler):
                break
        else:
            self.fail('No reporting LogHandler registered by default.')


class TestReportingConfiguration(TestCase):

    @mock.patch.object(reporting, 'instantiated_handler_registry')
    def test_empty_configuration_doesnt_add_handlers(
            self, instantiated_handler_registry):
        reporting.add_configuration({})
        self.assertEqual(
            0, instantiated_handler_registry.register_item.call_count)

    @mock.patch.object(
        reporting, 'instantiated_handler_registry', reporting.DictRegistry())
    @mock.patch.object(reporting, 'available_handlers')
    def test_looks_up_handler_by_type_and_adds_it(self, available_handlers):
        handler_type_name = 'test_handler'
        handler_cls = mock.Mock()
        available_handlers.registered_items = {handler_type_name: handler_cls}
        handler_name = 'my_test_handler'
        reporting.add_configuration(
            {handler_name: {'type': handler_type_name}})
        self.assertEqual(
            {handler_name: handler_cls.return_value},
            reporting.instantiated_handler_registry.registered_items)

    @mock.patch.object(
        reporting, 'instantiated_handler_registry', reporting.DictRegistry())
    @mock.patch.object(reporting, 'available_handlers')
    def test_uses_non_type_parts_of_config_dict_as_kwargs(
            self, available_handlers):
        handler_type_name = 'test_handler'
        handler_cls = mock.Mock()
        available_handlers.registered_items = {handler_type_name: handler_cls}
        extra_kwargs = {'foo': 'bar', 'bar': 'baz'}
        handler_config = extra_kwargs.copy()
        handler_config.update({'type': handler_type_name})
        handler_name = 'my_test_handler'
        reporting.add_configuration({handler_name: handler_config})
        self.assertEqual(
            handler_cls.return_value,
            reporting.instantiated_handler_registry.registered_items[
                handler_name])
        self.assertEqual([mock.call(**extra_kwargs)],
                         handler_cls.call_args_list)

    @mock.patch.object(
        reporting, 'instantiated_handler_registry', reporting.DictRegistry())
    @mock.patch.object(reporting, 'available_handlers')
    def test_handler_config_not_modified(self, available_handlers):
        handler_type_name = 'test_handler'
        handler_cls = mock.Mock()
        available_handlers.registered_items = {handler_type_name: handler_cls}
        handler_config = {'type': handler_type_name, 'foo': 'bar'}
        expected_handler_config = handler_config.copy()
        reporting.add_configuration({'my_test_handler': handler_config})
        self.assertEqual(expected_handler_config, handler_config)


class TestReportingEventStack(TestCase):
    @mock.patch('cloudinit.reporting.report_finish_event')
    @mock.patch('cloudinit.reporting.report_start_event')
    def test_start_and_finish_success(self, report_start, report_finish):
        with reporting.ReportEventStack(name="myname", description="mydesc"):
            pass
        self.assertEqual(report_start.call_count, 1)
        report_start.assert_called_with("myname", "mydesc")
        self.assertEqual(report_finish.call_count, 1)
        report_finish.assert_called_with(
            "myname", "mydesc", reporting.status.SUCCESS)

    @mock.patch('cloudinit.reporting.report_finish_event')
    @mock.patch('cloudinit.reporting.report_start_event')
    def test_finish_exception_defaults_fail(self, report_start, report_finish):
        name = "myname"
        desc = "mydesc"
        try:
            with reporting.ReportEventStack(name, description=desc):
                raise ValueError("This didnt work")
        except ValueError:
            pass
        self.assertEqual(report_start.call_count, 1)
        report_start.assert_called_with(name, desc)
        self.assertEqual(report_finish.call_count, 1)
        report_finish.assert_called_with(name, desc, reporting.status.FAIL)

    @mock.patch('cloudinit.reporting.report_finish_event')
    @mock.patch('cloudinit.reporting.report_start_event')
    def test_stop_exception_explicit_set(self, report_start, report_finish):
        name = "myname"
        desc = "mydesc"
        try:
            with reporting.ReportEventStack(
                    name, desc, result_on_exception=reporting.status.WARN):
                raise ValueError("This didnt work")
        except ValueError:
            pass
        self.assertEqual(report_start.call_count, 1)
        report_start.assert_called_with(name, desc)
        self.assertEqual(report_finish.call_count, 1)
        report_finish.assert_called_with(name, desc, reporting.status.WARN)

    @mock.patch('cloudinit.reporting.report_start_event')
    def test_child_fullname_respects_parent(self, report_start):
        parent_name = "topname"
        c1_name = "c1name"
        c2_name = "c2name"
        c2_expected_fullname = '/'.join([parent_name, c1_name, c2_name])
        c1_expected_fullname = '/'.join([parent_name, c1_name])

        parent = reporting.ReportEventStack(parent_name, "topdesc")
        c1 = reporting.ReportEventStack(c1_name, "c1desc", parent=parent)
        c2 = reporting.ReportEventStack(c2_name, "c2desc", parent=c1)

        with c1:
            report_start.assert_called_with(c1_expected_fullname, "c1desc")
            with c2:
                report_start.assert_called_with(c2_expected_fullname, "c2desc")

    @mock.patch('cloudinit.reporting.report_finish_event')
    @mock.patch('cloudinit.reporting.report_start_event')
    def test_child_result_bubbles_up(self, report_start, report_finish):
        parent = reporting.ReportEventStack("topname", "topdesc")
        child = reporting.ReportEventStack("c_name", "c_desc", parent=parent)
        with parent:
            with child:
                child.result = reporting.status.WARN

        report_finish.assert_called_with(
            "topname", "topdesc", reporting.status.WARN)
