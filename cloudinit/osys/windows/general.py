# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

"""General utilities for Windows platform."""

import ctypes

from cloudinit import exceptions
from cloudinit.osys import general
from cloudinit.osys.windows.util import kernel32


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
