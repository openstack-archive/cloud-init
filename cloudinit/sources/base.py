# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import abc
import itertools
import logging

import six

from cloudinit import exceptions
from cloudinit import plugin_finder
from cloudinit import sources


LOG = logging.getLogger(__name__)


class APIResponse(object):
    """Holds API response content

    To access the content in the binary format, use the
    `buffer` attribute, while the unicode content can be
    accessed by calling `str` over this (or by accessing
    the `decoded_buffer` property).
    """

    def __init__(self, buffer, encoding="utf-8"):
        self.buffer = buffer
        self.encoding = encoding
        self._decoded_buffer = None

    @property
    def decoded_buffer(self):
        # Avoid computing this again and again (although multiple threads
        # may decode it if they all get in here at the same time, but meh
        # thats ok).
        if self._decoded_buffer is None:
            self._decoded_buffer = self.buffer.decode(self.encoding)
        return self._decoded_buffer

    def __str__(self):
        return self.decoded_buffer


class DataSourceFinder(plugin_finder.ModuleFinder):
    """A finder which knows how to find all the possible data sources

    For retrieving the data sources that this finder knows about,
    use the :meth:`data_sources` method.
    """

    @staticmethod
    def _implements_source_api(module):
        """Check if the given module implements the data source API."""
        return hasattr(module, 'data_sources')

    def list_valid_modules(self):
        modules = self.list_all_modules()
        return [module for (_, _, module) in modules
                if self._implements_source_api(module)]

    def data_sources(self):
        data_sources = itertools.chain.from_iterable(
            module.data_sources()
            for module in self.list_valid_modules())
        return list(data_sources)


class DataSourceLoader(object):
    """Class for retrieving an available data source instance."""

    def __init__(self, search_paths):
        self._finder = DataSourceFinder(search_paths)

    def load_data_source(self):
        # TODO(cpopa): implement search strategies,
        # which should find data sources in parallel,
        # or filter the possible data sources
        # (return only network data sources)

        for data_source in self._finder.data_sources():
            instance = data_source()
            try:
                if instance.load():
                    return instance
            except Exception:
                LOG.error("Failed to load data source %r", data_source)

        raise exceptions.CloudInitError('No available data source found')


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
        """Retrieve the metadata exported under the `path` key.

        This should return an instance of :class:`APIResponse`.
        """

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


def get_data_source():
    """Get an instance of any data source available.

    This will usually return the first data source that could be loaded.
    """
    finder = DataSourceLoader(sources.__path__)
    return finder.load_data_source()
