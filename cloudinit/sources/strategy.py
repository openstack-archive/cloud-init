# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import abc

import six

from cloudinit import logging


LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseSearchStrategy(object):
    """Declare search strategies for data sources

    A *search strategy* represents a decoupled way of choosing
    one or more data sources from a list of data sources.
    Each strategy can be used interchangeably and they can
    be composed. For instance, once can apply a filtering strategy
    over a parallel search strategy, which looks for the available
    data sources.
    """

    @abc.abstractmethod
    def search_data_sources(self, data_sources):
        """Search the possible data sources for this strategy

        The method should filter the data sources that can be
        considered *valid* for the given strategy.

        :param data_sources:
            An iterator of data source instances, where the lookup
            will be done.
        """

    @staticmethod
    def is_datasource_available(data_source):
        """Check if the given *data_source* is considered *available*

        A data source is considered available if it can be loaded,
        but other strategies could implement their own behaviour.
        """
        try:
            if data_source.load():
                return True
        except Exception:
            LOG.error("Failed to load data source %r", data_source)
        return False


class FilterNameStrategy(BaseSearchStrategy):
    """A strategy for filtering data sources by name

    :param names:
        A list of strings, where each string is a name for a possible
        data source. Only the data sources that are in this list will
        be loaded and filtered.
    """

    def __init__(self, names=None):
        self._names = names
        super(FilterNameStrategy, self).__init__()

    def search_data_sources(self, data_sources):
        return (source for source in data_sources
                if source.__class__.__name__ in self._names)


class SerialSearchStrategy(BaseSearchStrategy):
    """A strategy that chooses a data source in serial."""

    def search_data_sources(self, data_sources):
        for data_source in data_sources:
            if self.is_datasource_available(data_source):
                yield data_source
