# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import cloudinit.shell as shell

from cloudinit.tests import TestCase
from cloudinit.tests.util import mock


class TestCase(TestCase):

    @mock.patch('cloudinit.shell.main_version')
    def test_main_has_version(self, main_version):
        shell.main(args=['cloud-init', 'version'])
        self.assertEqual(main_version.call_count, 1)

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
