# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import importlib
import subprocess
import unittest

from cloudinit import exceptions
from cloudinit.tests.util import mock


class TestNetworkWindows(unittest.TestCase):

    def setUp(self):
        self._ctypes_mock = mock.MagicMock()
        self._moves_mock = mock.Mock()
        self._win32com_mock = mock.Mock()
        self._wmi_mock = mock.Mock()

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

    def test__get_forward_table_no_memory(self):
        self._network_module._heap_alloc = mock.Mock()
        error_msg = 'Unable to allocate memory for the IP forward table'
        exc = exceptions.CloudinitError(error_msg)
        self._network_module._heap_alloc.side_effect = exc

        with self.assertRaises(exceptions.CloudinitError) as cm:
            with self._network._get_forward_table():
                pass

        self.assertEqual(error_msg, str(cm.exception))
        self._network_module._heap_alloc.assert_called_once_with(
            self._kernel32.GetProcessHeap.return_value,
            self._ctypes_mock.wintypes.ULONG.return_value)

    def test__get_forward_table_insufficient_buffer_no_memory(self):
        self._kernel32.HeapAlloc.side_effect = (mock.sentinel.table_mem, None)
        self._iphlpapi.GetIpForwardTable.return_value = (
            self._iphlpapi.ERROR_INSUFFICIENT_BUFFER)

        with self.assertRaises(exceptions.CloudinitError):
            with self._network._get_forward_table():
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

    def _test__get_forward_table(self, reallocation=False,
                                 insufficient_buffer=False,
                                 fail=False):
        if fail:
            with self.assertRaises(exceptions.CloudinitError) as cm:
                with self._network._get_forward_table():
                    pass

            msg = ('Unable to get IP forward table. Error: %s'
                   % mock.sentinel.error)
            self.assertEqual(msg, str(cm.exception))
        else:
            with self._network._get_forward_table() as table:
                pass
            pointer = self._ctypes_mock.POINTER(
                self._iphlpapi.Win32_MIB_IPFORWARDTABLE)
            expected_forward_table = self._ctypes_mock.cast(
                self._kernel32.HeapAlloc.return_value, pointer)
            self.assertEqual(expected_forward_table, table)

        heap_calls = [
            mock.call(self._kernel32.GetProcessHeap.return_value, 0,
                      self._ctypes_mock.cast.return_value)
        ]
        forward_calls = [
            mock.call(self._ctypes_mock.cast.return_value,
                      self._ctypes_mock.byref.return_value, 0),
        ]
        if insufficient_buffer:
            # We expect two calls for GetIpForwardTable
            forward_calls.append(forward_calls[0])
        if reallocation:
            heap_calls.append(heap_calls[0])
        self.assertEqual(heap_calls, self._kernel32.HeapFree.mock_calls)
        self.assertEqual(forward_calls,
                         self._iphlpapi.GetIpForwardTable.mock_calls)

    def test__get_forward_table_sufficient_buffer(self):
        self._iphlpapi.GetIpForwardTable.return_value = None
        self._test__get_forward_table()

    def test__get_forward_table_insufficient_buffer_reallocate(self):
        self._kernel32.HeapAlloc.side_effect = (
            mock.sentinel.table_mem, mock.sentinel.table_mem)
        self._iphlpapi.GetIpForwardTable.side_effect = (
            self._iphlpapi.ERROR_INSUFFICIENT_BUFFER, None)

        self._test__get_forward_table(reallocation=True,
                                      insufficient_buffer=True)

    def test__get_forward_table_insufficient_buffer_other_error(self):
        self._kernel32.HeapAlloc.side_effect = (
            mock.sentinel.table_mem, mock.sentinel.table_mem)
        self._iphlpapi.GetIpForwardTable.side_effect = (
            self._iphlpapi.ERROR_INSUFFICIENT_BUFFER, mock.sentinel.error)

        self._test__get_forward_table(reallocation=True,
                                      insufficient_buffer=True,
                                      fail=True)

    @mock.patch('cloudinit.osys.windows.network.Network.routes')
    def test_default_gateway_no_gateway(self, mock_routes):
        mock_routes.return_value = iter((mock.Mock(), mock.Mock()))

        self.assertIsNone(self._network.default_gateway())

        mock_routes.assert_called_once_with()

    @mock.patch('cloudinit.osys.windows.network.Network.routes')
    def test_default_gateway(self, mock_routes):
        default_gateway = mock.Mock()
        default_gateway.destination = '0.0.0.0'
        mock_routes.return_value = iter((mock.Mock(), default_gateway))

        gateway = self._network.default_gateway()

        self.assertEqual(default_gateway, gateway)

    def test_route_is_static(self):
        bad_route = self._network_module.Route(
            destination=None, netmask=None,
            gateway=None, interface=None, metric=None,
            flags=404)
        good_route = self._network_module.Route(
            destination=None, netmask=None,
            gateway=None, interface=None, metric=None,
            flags=self._network_module.MIB_IPPROTO_NETMGMT)

        self.assertTrue(good_route.is_static)
        self.assertFalse(bad_route.is_static)

    @mock.patch('subprocess.Popen')
    def _test_route_add(self, mock_popen, err):
        mock_route = mock.Mock()
        mock_route.destination = mock.sentinel.destination
        mock_route.netmask = mock.sentinel.netmask
        mock_route.gateway = mock.sentinel.gateway
        args = ['ROUTE', 'ADD', mock.sentinel.destination,
                'MASK', mock.sentinel.netmask,
                mock.sentinel.gateway]
        mock_popen.return_value.returncode = err
        mock_popen.return_value.communicate.return_value = (None, err)

        if err:
            with self.assertRaises(exceptions.CloudinitError) as cm:
                self._network_module.Route.add(mock_route)

            msg = "Unable to add route: %s" % err
            self.assertEqual(msg, str(cm.exception))

        else:
            self._network_module.Route.add(mock_route)
        mock_popen.assert_called_once_with(args, shell=False,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)

    def test_route_add_fails(self):
        self._test_route_add(err=1)

    def test_route_add_works(self):
        self._test_route_add(err=0)
