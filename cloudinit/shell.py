# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

from cloudinit import logging

LOG = logging.getLogger(__name__)


def load_file(path, encoding='utf8'):
    LOG.blather("Loading file from path '%s' (%s)", path, encoding)
    with open(path, 'rb') as fh:
        return fh.read().decode(encoding)
