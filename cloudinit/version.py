# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import pkg_resources

try:
    from pbr import version as pbr_version
    _version_info = pbr_version.VersionInfo('cloudinit')
    version_string = _version_info.version_string
except ImportError:  # pragma: nocover
    _version_info = pkg_resources.get_distribution('cloudinit')
    version_string = lambda: _version_info.version
