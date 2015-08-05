# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import abc
import itertools

import six

from cloudinit import exceptions
from cloudinit import logging
from cloudinit import sources
from cloudinit.sources import strategy


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


class DataSourceLoader(object):
    """Class for retrieving an available data source instance

    :param module_iterator:
        An instance of :class:`cloudinit.plugin_finder.BaseModuleIterator`,
        which is used to find possible modules where the data sources
        can be found.

    :param strategies:
        An iterator of search strategy classes, where each strategy is capable
        of filtering the data sources that can be used by cloudinit.
        Possible strategies includes serial data source search or
        parallel data source or filtering data sources according to
        some criteria (only network data sources)

     :param names:
        A list of possible data source names, from which the loader
        should pick. This can be used to filter the data sources
        that can be found from outside of cloudinit control.
    """

    def __init__(self, names, module_iterator, strategies):
        self._names = names
        self._module_iterator = module_iterator
        self._strategies = strategies

    @staticmethod
    def _implements_source_api(module):
        """Check if the given module implements the data source API."""
        return hasattr(module, 'data_sources')

    def _valid_modules(self):
        """Return all the modules that are *valid*

        Valid modules are those that implements a particular API
        for declaring the data sources it exports.
        """
        modules = self._module_iterator.list_modules()
        return filter(self._implements_source_api, modules)

    def all_data_sources(self):
        """Get all the data source classes that this finder knows about."""
        return itertools.chain.from_iterable(
            module.data_sources()
            for module in self._valid_modules())

    def valid_data_sources(self):
        """Get the data sources that are valid for this run."""
        data_sources = self.all_data_sources()
        # Instantiate them before passing to the strategies.
        data_sources = (data_source() for data_source in data_sources)

        for strategy_instance in self._strategies:
            data_sources = strategy_instance.search_data_source(data_sources)
        return data_sources


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


def get_data_source(names, module_iterator, strategies):
    """Get an instance of any data source available.

    :param names:
        A list of possible data source names, from which the loader
        should pick. This can be used to filter the data sources
        that can be found from outside of cloudinit control.

    :param module_iterator:
        A subclass of :class:`cloudinit.plugin_finder.BaseModuleIterator`,
        which is used to find possible modules where the data sources
        can be found.

    :param strategies:
        An iterator of search strategy classes, where each strategy is capable
        of filtering the data sources that can be used by cloudinit.
    """
    default_strategies = [strategy.FilterNameStrategy(names)]
    strategy_instances = [strategy_cls() for strategy_cls in strategies]
    strategies = default_strategies + strategy_instances

    iterator = module_iterator(sources.__path__)
    loader = DataSourceLoader(names, iterator, strategies)
    valid_sources = loader.valid_data_sources()

    try:
        return list(valid_sources)[0]
    except IndexError:
        raise exceptions.CloudInitError('No available data source found')
