# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

"""General utilities for Windows platform."""

import ctypes
import logging

from six.moves.urllib import parse
from six.moves.urllib import request

from cloudinit import exceptions
from cloudinit.osys import base
from cloudinit.osys import general
from cloudinit.osys.windows.util import kernel32


LOG = logging.getLogger(__name__)
MAX_URL_CHECK_RETRIES = 3


def _check_url(url, retries_count=MAX_URL_CHECK_RETRIES):
    for _ in range(retries_count):
        try:
            LOG.debug("Testing url: %s", url)
            request.urlopen(url)
            return True
        except Exception:
            pass
    return False


class General(general.General):
    """General utilities namespace for Windows."""

    @staticmethod
    def check_os_version(major, minor, build=0):
        """Check if this OS version is equal or higher than (major, minor)"""

        version_info = kernel32.Win32_OSVERSIONINFOEX_W()
        version_info.dwOSVersionInfoSize = ctypes.sizeof(
            kernel32.Win32_OSVERSIONINFOEX_W)

        version_info.dwMajorVersion = major
        version_info.dwMinorVersion = minor
        version_info.dwBuildNumber = build

        mask = 0
        for type_mask in [kernel32.VER_MAJORVERSION,
                          kernel32.VER_MINORVERSION,
                          kernel32.VER_BUILDNUMBER]:
            mask = kernel32.VerSetConditionMask(mask, type_mask,
                                                kernel32.VER_GREATER_EQUAL)

        type_mask = (kernel32.VER_MAJORVERSION |
                     kernel32.VER_MINORVERSION |
                     kernel32.VER_BUILDNUMBER)
        ret_val = kernel32.VerifyVersionInfoW(ctypes.byref(version_info),
                                              type_mask, mask)
        if ret_val:
            return True
        else:
            err = kernel32.GetLastError()
            if err == kernel32.ERROR_OLD_WIN_VERSION:
                return False
            else:
                raise exceptions.CloudInitError(
                    "VerifyVersionInfo failed with error: %s" % err)

    def reboot(self):
        raise NotImplementedError

    def set_locale(self, locale):
        raise NotImplementedError

    def set_timezone(self, timezone):
        raise NotImplementedError

    def set_metadata_ip_route(self, metadata_url):
        """Set a network route if the given metadata url can't be accessed.

        This is a workaround for https://bugs.launchpad.net/quantum/+bug/1174657.
        """
        osutils = base.get_osutils()

        if self.check_os_version(6, 0):
            # 169.254.x.x addresses are not getting routed starting from
            # Windows Vista / 2008
            metadata_netloc = parse.urlparse(metadata_url).netloc
            metadata_host = metadata_netloc.split(':')[0]

            if not metadata_host.startswith("169.254."):
                return

            routes = osutils.network.routes()
            if metadata_host in routes and not _check_url(metadata_url):
                default_gateway = osutils.network.default_gateway()
                if default_gateway:
                    try:
                        LOG.debug('Setting gateway for host: %s',
                                  metadata_host)
                        route = osutils.route_class(
                            destination=metadata_host,
                            netmask="255.255.255.255",
                            gateway=default_gateway.destination)
                        osutils.route_class.add(route)
                    except Exception as ex:
                        # Ignore it
                        LOG.exception(ex)
