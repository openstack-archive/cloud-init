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


class TestNetworkWindows(unittest.TestCase):

    def setUp(self):
        self._ctypes_mock = mock.MagicMock()
        self._moves_mock = mock.MagicMock()
        self._win32com_mock = mock.MagicMock()
        self._wmi_mock = mock.MagicMock()

        self._module_patcher = mock.patch.dict(
            'sys.modules',
            {'ctypes': self._ctypes_mock,
             'win32com': self._win32com_mock,
             'wmi': self._wmi_mock,
             'six.moves': self._moves_mock})

        self._module_patcher.start()
        self._iphlpapi = mock.Mock()
        self._kernel32 = mock.Mock()
        self._ws2_32 = mock.Mock()

        self._network_module = importlib.import_module(
            'cloudinit.osys.windows.network')
        self._network_module.iphlpapi = self._iphlpapi
        self._network_module.kernel32 = self._kernel32
        self._network_module.ws2_32 = self._ws2_32

        self._network = self._network_module.Network()

    def tearDown(self):
        self._module_patcher.stop()

    def _test__heap_alloc(self, fail):
        mock_heap = mock.Mock()
        mock_size = mock.Mock()

        if fail:
            self._kernel32.HeapAlloc.return_value = None

            with self.assertRaises(exceptions.CloudinitError) as cm:
                self._network_module._heap_alloc(mock_heap, mock_size)

            self.assertEqual('Unable to allocate memory for the IP '
                             'forward table',
                             str(cm.exception))
        else:
            result = self._network_module._heap_alloc(mock_heap, mock_size)
            self.assertEqual(self._kernel32.HeapAlloc.return_value, result)

        self._kernel32.HeapAlloc.assert_called_once_with(
            mock_heap, 0, self._ctypes_mock.c_size_t(mock_size.value))

    def test__heap_alloc_error(self):
        self._test__heap_alloc(fail=True)

    def test__heap_alloc_no_error(self):
        self._test__heap_alloc(fail=False)

    def test__allocate_forward_table_no_memory(self):
        self._network_module._heap_alloc = mock.Mock()
        error_msg = 'Unable to allocate memory for the IP forward table'
        exc = exceptions.CloudinitError(error_msg)
        self._network_module._heap_alloc.side_effect = exc

        with self.assertRaises(exceptions.CloudinitError) as cm:
            with self._network._allocate_forward_table():
                pass

        self.assertEqual(error_msg, str(cm.exception))
        self._network_module._heap_alloc.assert_called_once_with(
            self._kernel32.GetProcessHeap.return_value,
            self._ctypes_mock.wintypes.ULONG.return_value)

    def test__allocate_forward_table_insufficient_buffer_no_memory(self):
        self._kernel32.HeapAlloc.side_effect = (mock.sentinel.table_mem, None)
        self._iphlpapi.GetIpForwardTable.return_value = (
            self._iphlpapi.ERROR_INSUFFICIENT_BUFFER)

        with self.assertRaises(exceptions.CloudinitError):
            with self._network._allocate_forward_table():
                pass

        table = self._ctypes_mock.cast.return_value
        self._iphlpapi.GetIpForwardTable.assert_called_once_with(
            table,
            self._ctypes_mock.byref.return_value, 0)
        heap_calls = [
            mock.call(self._kernel32.GetProcessHeap.return_value, 0, table),
            mock.call(self._kernel32.GetProcessHeap.return_value, 0, table)
        ]
        self.assertEqual(heap_calls, self._kernel32.HeapFree.mock_calls)

    def _test__allocate_forward_table(self, reallocation=False):
        with self._network._allocate_forward_table() as (table, size):
            self._iphlpapi.GetIpForwardTable.assert_called_once_with(
                table, self._ctypes_mock.byref.return_value, 0)
            pointer = self._ctypes_mock.POINTER(
                self._iphlpapi.Win32_MIB_IPFORWARDTABLE)
            forward_table_size = self._ctypes_mock.sizeof(
                self._iphlpapi.Win32_MIB_IPFORWARDTABLE)
            expected_forward_table = self._ctypes_mock.cast(
                self._kernel32.HeapAlloc.return_value, pointer)
            expected_size = self._ctypes_mock.wintypes.ULONG(
                forward_table_size)
            self.assertEqual(expected_forward_table, table)
            self.assertEqual(expected_size, size)

        heap_calls = [
            mock.call(self._kernel32.GetProcessHeap.return_value, 0, table),
        ]
        if reallocation:
            heap_calls.append(heap_calls[0])
        self.assertEqual(heap_calls, self._kernel32.HeapFree.mock_calls)

    def test__allocate_forward_table_sufficient_buffer(self):
        self._test__allocate_forward_table()

    def test__allocate_forward_table_insufficient_buffer_reallocate(self):
        self._kernel32.HeapAlloc.side_effect = (
            mock.sentinel.table_mem, mock.sentinel.table_mem)
        self._iphlpapi.GetIpForwardTable.return_value = (
            self._iphlpapi.ERROR_INSUFFICIENT_BUFFER)

        self._test__allocate_forward_table(reallocation=True)
