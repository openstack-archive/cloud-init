# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

"""Base classes for interacting with OpenStack data sources."""

import json
import os
import posixpath

from cloudinit.sources import base

__all__ = ('BaseOpenStackSource', )

_METADATA_NETWORK_KEY = "content_path"
_ADMIN_PASSWORD = "admin_pass"


class BaseOpenStackSource(base.BaseDataSource):
    """Base classes for interacting with an OpenStack data source.

    This is useful for both the HTTP data source, as well for
    ConfigDrive.
    """

    def _get_content(self, name):
        path = posixpath.normpath(
            posixpath.join('openstack', 'content', name))
        return self._get_cache_data(path)

    def _get_meta_data(self, version='latest'):
        path = posixpath.normpath(
            posixpath.join('openstack', version, 'meta_data.json'))
        data = self._get_cache_data(path)
        if data:
            return json.loads(data.decode(encoding='utf-8'))

    def user_data(self):
        path = posixpath.normpath(
            posixpath.join('openstack', 'latest', 'user_data'))
        return self._get_cache_data(path)

    def vendor_data(self):
        path = posixpath.normpath(
            posixpath.join('openstack', 'latest', 'vendor_data.json'))
        return self._get_cache_data(path)

    def instance_id(self):
        return self._get_meta_data().get('uuid')

    def host_name(self):
        return self._get_meta_data().get('hostname')

    def public_keys(self):
        public_keys = self._get_meta_data().get('public_keys')
        if public_keys:
            return list(public_keys.values())

    def network_config(self):
        network_config = self._get_meta_data().get('network_config')
        if not network_config:
            return None
        if _METADATA_NETWORK_KEY not in network_config:
            return None

        content_path = network_config[_METADATA_NETWORK_KEY]
        content_name = os.path.basename(content_path)
        return self._get_content(content_name)

    def admin_password(self):
        meta_data = self._get_meta_data()
        meta = meta_data.get('meta', {})
        return meta.get(_ADMIN_PASSWORD) or meta_data.get(_ADMIN_PASSWORD)
