# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import logging
import sys

from six.moves.urllib import parse
from six.moves.urllib import request

from cloudinit.osys import base


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


def set_metadata_ip_route(metadata_url):
    """Set a network route if the given metadata url can't be accessed.

    This is a workaround for https://bugs.launchpad.net/quantum/+bug/1174657
    and it's a no-op on non-Windows systems.
    """

    osutils = base.get_osutils()

    if sys.platform == 'win32' and osutils.general.check_os_version(6, 0):
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
