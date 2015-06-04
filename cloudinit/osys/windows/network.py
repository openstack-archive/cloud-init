# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

"""Network utilities for Windows."""

import contextlib
import ctypes
from ctypes import wintypes
import logging
import subprocess

from six.moves import winreg

from cloudinit import exceptions
from cloudinit.osys import network
from cloudinit.osys.windows.util import iphlpapi
from cloudinit.osys.windows.util import kernel32
from cloudinit.osys.windows.util import ws2_32


_MIB_IPPROTO_NETMGMT = 3
_FW_IP_PROTOCOL_TCP = 6
_FW_IP_PROTOCOL_UDP = 17
_FW_SCOPE_ALL = 0
_PROTOCOL_TCP = "TCP"
_PROTOCOL_UDP = "UDP"
_ERROR_FILE_NOT_FOUND = 2
_ComputerNamePhysicalDnsHostname = 5
LOG = logging.getLogger(__file__)


def _format_mac_address(phys_address, phys_address_len):
    address = phys_address[:phys_address_len]
    return ":".join(("%02X" % byte for byte in address))


def _socket_addr_to_str(socket_addr):
    addr_str_len = wintypes.DWORD(256)
    addr_str = ctypes.create_unicode_buffer(256)

    ret_val = ws2_32.WSAAddressToStringW(
        socket_addr.lpSockaddr,
        socket_addr.iSockaddrLength,
        None, addr_str, ctypes.byref(addr_str_len))
    if ret_val:
        raise exceptions.CloudinitError("WSAAddressToStringW failed: %s"
                                        % ws2_32.WSAGetLastError())

    return addr_str.value


def _get_registry_dhcp_server(adapter_name):
    with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            "SYSTEM\\CurrentControlSet\\Services\\" +
            "Tcpip\\Parameters\\Interfaces\\%s" % adapter_name, 0,
            winreg.KEY_READ) as key:
        try:
            dhcp_server = winreg.QueryValueEx(key, "DhcpServer")[0]
            if dhcp_server == "255.255.255.255":
                dhcp_server = None
            return dhcp_server
        except Exception as ex:
            # Not found
            if ex.errno != _ERROR_FILE_NOT_FOUND:
                raise


class Network(network.Network):
    """Network namespace object tailored for the Windows platform."""

    @staticmethod
    @contextlib.contextmanager
    def _allocate_forward_table():
        heap = kernel32.GetProcessHeap()
        forward_table_size = ctypes.sizeof(iphlpapi.Win32_MIB_IPFORWARDTABLE)
        size = wintypes.ULONG(forward_table_size)
        table_mem = kernel32.HeapAlloc(heap, 0, ctypes.c_size_t(size.value))
        if not table_mem:
            raise exceptions.CloudinitError(
                'Unable to allocate memory for the IP forward table')

        p_forward_table = ctypes.cast(
            table_mem, ctypes.POINTER(iphlpapi.Win32_MIB_IPFORWARDTABLE))

        try:
            err = iphlpapi.GetIpForwardTable(p_forward_table,
                                             ctypes.byref(size), 0)
            if err == iphlpapi.ERROR_INSUFFICIENT_BUFFER:
                kernel32.HeapFree(heap, 0, p_forward_table)
                table_mem = kernel32.HeapAlloc(
                    heap, 0, ctypes.c_size_t(size.value))
                if not table_mem:
                    raise exceptions.CloudinitError(
                        'Unable to allocate memory for the IP forward table')

                p_forward_table = ctypes.cast(
                    table_mem,
                    ctypes.POINTER(iphlpapi.Win32_MIB_IPFORWARDTABLE))
            yield p_forward_table, size
        finally:
            kernel32.HeapFree(heap, 0, p_forward_table)

    def routes(self):
        """Get a collection of the available routes."""
        routing_table = []
        with self._allocate_forward_table() as (p_forward_table, size):
            err = iphlpapi.GetIpForwardTable(p_forward_table,
                                             ctypes.byref(size), 0)
            if err != kernel32.ERROR_NO_DATA:
                if err:
                    raise exceptions.CloudinitError(
                        'Unable to get IP forward table. Error: %s' % err)

                forward_table = p_forward_table.contents
                table = ctypes.cast(
                    ctypes.addressof(forward_table.table),
                    ctypes.POINTER(iphlpapi.Win32_MIB_IPFORWARDROW *
                                   forward_table.dwNumEntries)).contents

                for row in table:
                    destination = ws2_32.Ws2_32.inet_ntoa(
                        row.dwForwardDest).decode()
                    netmask = ws2_32.Ws2_32.inet_ntoa(
                        row.dwForwardMask).decode()
                    gateway = ws2_32.Ws2_32.inet_ntoa(
                        row.dwForwardNextHop).decode()
                    index = ws2_32.Ws2_32.dwForwardIfIndex
                    flags = ws2_32.Ws2_32.dwForwardProto
                    metric = row.dwForwardMetric1
                    route = Route(destination=destination,
                                  gateway=gateway,
                                  netmask=netmask,
                                  interface=index,
                                  metric=metric,
                                  flags=flags)
                    routing_table.append(route)

            return routing_table

    def default_gateway(self):
        """Get the default gateway.

        This will actually return a :class:`Route` instance. The gateway
        can be accessed with the :attr:`gateway` attribute.
        """
        return next((r for r in self.routes() if r.destination == '0.0.0.0'),
                    None)

    # These are not required by the Windows version for now,
    # but we provide them as noop version.
    def hosts(self):
        """Grab the content of the hosts file."""

    def interfaces(self):
        pass

    def set_hostname(self, hostname):
        pass

    def set_static_network_config(self, adapter_name, address, netmask,
                                  broadcast, gateway, dnsnameservers):
        pass


class Route(network.Route):
    """Windows route class."""

    @property
    def is_static(self):
        return self.flags == _MIB_IPPROTO_NETMGMT

    @classmethod
    def add(cls, route):
        """Add a new route in the underlying OS.

        The function should expect an instance of :class:`Route`.
        """
        args = ['ROUTE', 'ADD',
                route.destination,
                'MASK', route.netmask, route.gateway]
        popen = subprocess.Popen(args, shell=False,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        _, stderr = popen.communicate()
        if popen.returncode or stderr:
            # Cannot use the return value to determine the outcome
            raise exceptions.CloudinitError('Unable to add route: %s' % stderr)

    @classmethod
    def delete(cls, _):
        """Delete a route from the underlying OS.

        This function should expect an instance of :class:`Route`.
        """
