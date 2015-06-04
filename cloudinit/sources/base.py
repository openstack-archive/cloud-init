# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import abc
import time

import six


class MissingMetadataError(Exception):
    """Raised when the metadata can't be found where it is expected."""


@six.add_metaclass(abc.ABCMeta)
class BaseDataSource(object):
    """Base class for the data sources."""

    enable_retry = True
    retry_count = 1
    retry_interval = 1

    def __init__(self):
        self._cache = {}

    def _exec_retry(self, action, enable_retry=None,
                    retry_count=None,
                    retry_interval=None):
        """Retry the given action up to a number of given retries."""

        if enable_retry is None:
            enable_retry = self.enable_retry
        if retry_count is None:
            retry_count = self.retry_count
        if retry_interval is None:
            retry_interval = self.retry_interval

        index = 0
        while True:
            try:
                return action()
            except MissingMetadataError:
                raise
            except Exception:
                if enable_retry and index < retry_count:
                    index += 1
                    time.sleep(retry_interval)
                else:
                    raise

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
            self._cache[path] = self._exec_retry(lambda: self._get_data(path))

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

    @property
    def can_update_password(self):
        """Check if this data source can update the admin password."""

    def is_password_changed(self):
        """Check if the data source has a new password for this instance."""
