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

from six.moves import urllib_parse

from cloudinit import exceptions
from cloudinit.osys import base
from cloudinit.osys import network
from cloudinit.osys.windows.util import iphlpapi
from cloudinit.osys.windows.util import kernel32
from cloudinit.osys.windows.util import ws2_32
from cloudinit import url_helper


MIB_IPPROTO_NETMGMT = 3
_FW_IP_PROTOCOL_TCP = 6
_FW_IP_PROTOCOL_UDP = 17
_FW_SCOPE_ALL = 0
_PROTOCOL_TCP = "TCP"
_PROTOCOL_UDP = "UDP"
_ERROR_FILE_NOT_FOUND = 2
_ComputerNamePhysicalDnsHostname = 5
_MAX_URL_CHECK_RETRIES = 3
LOG = logging.getLogger(__name__)


def _heap_alloc(heap, size):
    table_mem = kernel32.HeapAlloc(heap, 0, ctypes.c_size_t(size.value))
    if not table_mem:
        raise exceptions.CloudInitError(
            'Unable to allocate memory for the IP forward table')
    return table_mem


def _check_url(url, retries_count=_MAX_URL_CHECK_RETRIES):
    LOG.debug("Testing url: %s", url)
    try:
        url_helper.read_url(url, retries=retries_count)
        return True
    except url_helper.UrlError:
        return False


class Network(network.Network):
    """Network namespace object tailored for the Windows platform."""

    @staticmethod
    @contextlib.contextmanager
    def _get_forward_table():
        heap = kernel32.GetProcessHeap()
        forward_table_size = ctypes.sizeof(iphlpapi.Win32_MIB_IPFORWARDTABLE)
        size = wintypes.ULONG(forward_table_size)
        table_mem = _heap_alloc(heap, size)

        p_forward_table = ctypes.cast(
            table_mem, ctypes.POINTER(iphlpapi.Win32_MIB_IPFORWARDTABLE))

        try:
            err = iphlpapi.GetIpForwardTable(p_forward_table,
                                             ctypes.byref(size), 0)
            if err == iphlpapi.ERROR_INSUFFICIENT_BUFFER:
                kernel32.HeapFree(heap, 0, p_forward_table)
                table_mem = _heap_alloc(heap, size)
                p_forward_table = ctypes.cast(
                    table_mem,
                    ctypes.POINTER(iphlpapi.Win32_MIB_IPFORWARDTABLE))
                err = iphlpapi.GetIpForwardTable(p_forward_table,
                                                 ctypes.byref(size), 0)

            if err and err != kernel32.ERROR_NO_DATA:
                raise exceptions.CloudInitError(
                    'Unable to get IP forward table. Error: %s' % err)

            yield p_forward_table
        finally:
            kernel32.HeapFree(heap, 0, p_forward_table)

    def routes(self):
        """Get a collection of the available routes."""
        routing_table = []
        with self._get_forward_table() as p_forward_table:
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
                index = row.dwForwardIfIndex
                flags = row.dwForwardProto
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

    def set_metadata_ip_route(self, metadata_url):
        """Set a network route if the given metadata url can't be accessed.

        This is a workaround for
           https://bugs.launchpad.net/quantum/+bug/1174657.
        """
        osutils = base.get_osutils()

        if osutils.general.check_os_version(6, 0):
            # 169.254.x.x addresses are not getting routed starting from
            # Windows Vista / 2008
            metadata_netloc = urllib_parse.urlparse(metadata_url).netloc
            metadata_host = metadata_netloc.split(':')[0]

            if not metadata_host.startswith("169.254."):
                return

            routes = self.routes()
            exists_route = any(route.destination == metadata_host
                               for route in routes)
            if not exists_route and not _check_url(metadata_url):
                default_gateway = self.default_gateway()
                if default_gateway:
                    try:
                        LOG.debug('Setting gateway for host: %s',
                                  metadata_host)
                        route = Route(
                            destination=metadata_host,
                            netmask="255.255.255.255",
                            gateway=default_gateway.gateway,
                            interface=None, metric=None)
                        Route.add(route)
                    except Exception as ex:
                        # Ignore it
                        LOG.exception(ex)

    # These are not required by the Windows version for now,
    # but we provide them as noop version.
    def hosts(self):
        """Grab the content of the hosts file."""
        raise NotImplementedError

    def interfaces(self):
        raise NotImplementedError

    def set_hostname(self, hostname):
        raise NotImplementedError

    def set_static_network_config(self, adapter_name, address, netmask,
                                  broadcast, gateway, dnsnameservers):
        raise NotImplementedError


class Route(network.Route):
    """Windows route class."""

    @property
    def is_static(self):
        return self.flags == MIB_IPPROTO_NETMGMT

    @classmethod
    def add(cls, route):
        """Add a new route in the underlying OS.

        The function should expect an instance of :class:`Route`.
        """
        args = ['ROUTE', 'ADD',
                route.destination,
                'MASK', route.netmask, route.gateway]
        popen = subprocess.Popen(args, shell=False,
                                 stderr=subprocess.PIPE)
        _, stderr = popen.communicate()
        if popen.returncode or stderr:
            # Cannot use the return value to determine the outcome
            raise exceptions.CloudInitError('Unable to add route: %s' % stderr)

    @classmethod
    def delete(cls, _):
        """Delete a route from the underlying OS.

        This function should expect an instance of :class:`Route`.
        """
        raise NotImplementedError
