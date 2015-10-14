# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

"""Base classes for interacting with OpenStack data sources."""

import abc
import json
import logging
import os

import six

from cloudinit.sources import base

__all__ = ('BaseOpenStackSource', )

_PAYLOAD_KEY = "content_path"
_ADMIN_PASSWORD = "admin_pass"
LOG = logging.getLogger(__name__)
_OS_LATEST = 'latest'
_OS_FOLSOM = '2012-08-10'
_OS_GRIZZLY = '2013-04-04'
_OS_HAVANA = '2013-10-17'
# Keep this in chronological order. New supported versions go at the end.
_OS_VERSIONS = (
    _OS_FOLSOM,
    _OS_GRIZZLY,
    _OS_HAVANA,
)


@six.add_metaclass(abc.ABCMeta)
class BaseOpenStackSource(base.BaseDataSource):
    """Base classes for interacting with an OpenStack data source.

    This is useful for both the HTTP data source, as well for
    ConfigDrive.
    """
    def __init__(self):
        super(BaseOpenStackSource, self).__init__()
        self._version = None

    @abc.abstractmethod
    def _available_versions(self):
        """Get the available metadata versions."""

    @abc.abstractmethod
    def _path_join(self, path, *addons):
        """Join one or more components together."""

    def version(self):
        """Get the underlying data source version."""
        return self._version

    def _working_version(self):
        versions = self._available_versions()
        # OS_VERSIONS is stored in chronological order, so
        # reverse it to check newest first.
        supported = reversed(_OS_VERSIONS)
        selected_version = next((version for version in supported
                                 if version in versions), _OS_LATEST)

        LOG.debug("Selected version %r from %s", selected_version, versions)
        return selected_version

    def load(self):
        self._version = self._working_version()
        super(BaseOpenStackSource, self).load()

    def _get_data_helper(self, filename, sub_path):
        path = self._path_join('openstack', sub_path, filename)
        data = self._get_cache_data(path)
        if data and filename.endswith('json'):
            return json.loads(str(data))
        elif data:
            return data
        else:
            return dict()

    def _get_content(self, name):
        return self._get_data_helper(name, 'content')

    def _get_meta_data(self):
        return self._get_data_helper('meta_data.json', self._version)

    def user_data(self):
        return self._get_data_helper('user_data', self._version)

    def vendor_data(self):
        return self._get_data_helper('vendor_data.json', self._version)

    def network_data(self):
        return self._get_data_helper('network_data.json', self._version)

    def instance_id(self):
        return self._get_meta_data().get('uuid')

    def host_name(self):
        return self._get_meta_data().get('hostname')

    def public_keys(self):
        public_keys = self._get_meta_data().get('public_keys')
        if public_keys:
            return list(public_keys.values())
        return []

    def network_config(self):
        net_config = self.network_data()
        if all(net_config.get(x) for x in ['links', 'networks', 'services']):
            return net_config  # returns dict
        else:
            for source in [self._get_meta_data(), self.vendor_data()]:
                net_config = source.get(
                    'network_config', {})

                if _PAYLOAD_KEY in net_config:
                    content_path = net_config[_PAYLOAD_KEY]
                    content_name = os.path.basename(content_path)
                    return str(self._get_content(content_name))

    def admin_password(self):
        meta_data = self._get_meta_data()
        meta = meta_data.get('meta', {})
        return meta.get(_ADMIN_PASSWORD) or meta_data.get(_ADMIN_PASSWORD)
