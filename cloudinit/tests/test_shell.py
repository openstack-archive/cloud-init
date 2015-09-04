# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import six

import cloudinit.shell as shell
from cloudinit.tests import TestCase
from cloudinit.tests.util import mock


class TestMain(TestCase):

    def test_help_exits_success(self):
        with mock.patch('cloudinit.shell.sys.stdout'):
            exc = self.assertRaises(
                SystemExit, shell.main, args=['cloud-init', '--help'])
            self.assertEqual(exc.code, 0)

    def test_invalid_arguments_exit_fail(self):
        # silence writes that get to stderr
        with mock.patch('cloudinit.shell.sys.stderr'):
            exc = self.assertRaises(
                SystemExit, shell.main, args=['cloud-init', 'bogus_argument'])
            self.assertNotEqual(exc.code, 0)

    @mock.patch('cloudinit.shell.sys.stdout')
    def test_version_shows_cloud_init(self, mock_out_write):
        shell.main(args=['cloud-init', 'version'])
        write_arg = mock_out_write.write.call_args[0][0]
        self.assertTrue(write_arg.startswith('cloud-init'))

    @mock.patch('cloudinit.shell.sys.stderr', new_callable=six.StringIO)
    def test_no_arguments_shows_usage(self, stderr):
        self.assertRaises(SystemExit, shell.main, args=['cloud-init'])
        self.assertIn('usage: cloud-init', stderr.getvalue())

    @mock.patch('cloudinit.shell.sys.stderr', mock.MagicMock())
    def test_no_arguments_exits_2(self):
        exc = self.assertRaises(SystemExit, shell.main, args=['cloud-init'])
        self.assertEqual(2, exc.code)

    @mock.patch('cloudinit.shell.sys.stderr', new_callable=six.StringIO)
    def test_no_arguments_shows_error_message(self, stderr):
        self.assertRaises(SystemExit, shell.main, args=['cloud-init'])
        self.assertIn('cloud-init: error: too few arguments',
                      stderr.getvalue())


class TestLoggingConfiguration(TestCase):

    @mock.patch('cloudinit.shell.sys.stderr', new_callable=six.StringIO)
    def test_log_to_console(self, stderr):
        shell.main(args=['cloud-init', '--log-to-console', 'version'])
        shell.logging.getLogger().info('test log message')
        self.assertIn('test log message', stderr.getvalue())

    @mock.patch('cloudinit.shell.sys.stderr', new_callable=six.StringIO)
    def test_log_to_console_not_default(self, stderr):
        shell.main(args=['cloud-init', 'version'])
        shell.logging.getLogger().info('test log message')
        self.assertNotIn('test log message', stderr.getvalue())
