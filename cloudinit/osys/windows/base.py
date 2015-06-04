# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

from cloudinit.osys import base
from cloudinit.osys.windows import general as general_module
from cloudinit.osys.windows import network as network_module


__all__ = ('OSUtils', )


class OSUtils(base.OSUtils):
    """The OS utils namespace for the Windows platform."""

    name = "windows"

    network = network_module.Network()
    general = general_module.General()
    route_class = network_module.Route

    # These aren't yet implemented, use `None` for them
    # so that we could instantiate the class.
    filesystem = user_class = users = None
    interface_class = None
