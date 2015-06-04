# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import importlib
import unittest

try:
    import unittest.mock as mock
except ImportError:
    import mock

from cloudinit import exceptions


class TestsWindowsGeneral(unittest.TestCase):

    def setUp(self):
        self._ctypes_mock = mock.MagicMock()

        self._module_patcher = mock.patch.dict(
            'sys.modules',
            {'ctypes': self._ctypes_mock})

        self._module_patcher.start()
        self._general_module = importlib.import_module(
            "cloudinit.osys.windows.general")
        self._kernel32 = self._general_module.kernel32
        self._windll_mock = self._ctypes_mock.windll
        self._general = self._general_module.General()

    def tearDown(self):
        self._module_patcher.stop()

    def _test_check_os_version(self, ret_value, error_value=None):
        verset_return = 2
        self._kernel32.Win32_OSVERSIONINFOEX_W = mock.Mock()
        self._windll_mock.kernel32.VerSetConditionMask.return_value = (
            verset_return)
        self._windll_mock.kernel32.VerifyVersionInfoW.return_value = ret_value
        self._windll_mock.kernel32.GetLastError.return_value = error_value

        old_version = self._kernel32.ERROR_OLD_WIN_VERSION

        if error_value and error_value is not old_version:
            self.assertRaises(exceptions.CloudinitError,
                              self._general.check_os_version, 3, 1, 2)
            self._kernel32.GetLastError.assert_called_once_with()

        else:
            response = self._general.check_os_version(3, 1, 2)
            self.assertEqual(self._kernel32, self._general_module.kernel32,
                             (self._kernel32, self._general_module.kernel32))
            self._kernel32.Win32_OSVERSIONINFOEX_W.assert_called_once_with()
            self._ctypes_mock.sizeof.assert_called_once_with(
                self._kernel32.Win32_OSVERSIONINFOEX_W)
            self.assertEqual(
                3, self._windll_mock.kernel32.VerSetConditionMask.call_count)

            mask = (self._kernel32.VER_MAJORVERSION |
                    self._kernel32.VER_MINORVERSION |
                    self._kernel32.VER_BUILDNUMBER)
            self._windll_mock.kernel32.VerifyVersionInfoW.assert_called_with(
                self._ctypes_mock.byref.return_value, mask, verset_return)

            if error_value is old_version:
                self._windll_mock.kernel32.GetLastError.assert_called_with()
                self.assertFalse(response)
            else:
                self.assertTrue(response)

    def test_check_os_version(self):
        m = mock.MagicMock()
        self._test_check_os_version(ret_value=m)

    def test_check_os_version_expect_false(self):
        self._test_check_os_version(
            ret_value=None, error_value=self._kernel32.ERROR_OLD_WIN_VERSION)
