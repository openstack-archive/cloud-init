# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import unittest
import sys
from six import StringIO

import cloudinit.shell as shell
from cloudinit.tests.util import mock

class TestMain(unittest.TestCase):

    @mock.patch('cloudinit.shell.main_version')
    def test_main_has_version(self, main_version):
        shell.main(args=['cloud-init', 'version'])
        self.assertEqual(main_version.call_count, 1)

    def test_help_exits_success(self):
        exit_code = "SYS_EXIT_NOT_CALLED"
        try:
            shell.main(args=['cloud-init', '--help'])
        except SystemExit as e:
            exit_code = e.code
        self.assertEqual(exit_code, 0)

    @mock.patch('sys.stderr.write')
    def test_invalid_exits_fail(self, mock_err_write):
        exit_code = 0
        bogus = 'bogus'
        try:
            shell.main(args=['cloud-init', bogus])
        except SystemExit as e:
            exit_code = e.code
        written = ''.join(
           f[0][0] for f in mock_err_write.call_args_list)
        self.assertIn(bogus, written)
        self.assertNotEqual(exit_code, 0)

    @mock.patch('sys.stdout.write')
    def test_version_shows_cloud_init(self, mock_out_write):
        shell.main(args=['cloud-init', 'version'])
        write_arg = mock_out_write.call_args[0][0]
        self.assertTrue(write_arg.startswith('cloud-init'))
