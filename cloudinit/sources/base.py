# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class BaseDataSource(object):
    """Base class for the data sources."""

    datasource_config = {}

    def __init__(self, config=None):
        self._cache = {}
        # TODO(cpopa): merge them instead.
        self._config = config or self.datasource_config

    def _get_cache_data(self, path):
        """Do a metadata lookup for the given *path*

        This will return the available metadata under *path*,
        while caching the result, so that a next call will not do
        an additional API call.
        The return value of this method can be bytes on Python 3,
        so make sure to decode the value to an unicode string
        (not doing this implicitly, since user data can be encoded
        with an unknown encoding).
        """
        if path not in self._cache:
            self._cache[path] = self._get_data(path)

        return self._cache[path]

    @abc.abstractmethod
    def load(self):
        """Try to load this metadata service.

        This should return ``True`` if the service was loaded properly,
        ``False`` otherwise.
        """

    @abc.abstractmethod
    def _get_data(self, path):
        """Retrieve the metadata exported under the `path` key."""

    def instance_id(self):
        """Get this instance's id."""

    def user_data(self):
        """Get the user data available for this instance."""

    def vendor_data(self):
        """Get the vendor data available for this instance."""

    def host_name(self):
        """Get the hostname available for this instance."""

    def public_keys(self):
        """Get the public keys available for this instance."""

    def network_config(self):
        """Get the specified network config, if any."""

    def admin_password(self):
        """Get the admin password."""

    def post_password(self, password):
        """Post the password to the metadata service."""

    def can_update_password(self):
        """Check if this data source can update the admin password."""

    def is_password_changed(self):
        """Check if the data source has a new password for this instance."""
        return False

    def is_password_set(self):
        """Check if the password was already posted to the metadata service."""
