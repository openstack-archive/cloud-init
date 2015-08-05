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
    a data source from a list of data sources, where the act of choosing
    can be serial, parallel or it can depend on certain filtering.
    Each strategy can be used interchangeably. Also, they can
    be composed, such as applying a filtering strategy over a parallel
    search strategy.
    """

    @abc.abstractmethod
    def search_data_source(self, data_sources):
        """Search the possible data sources for this strategy

        The method should filter the data sources that can be
        considered *valid* for the given strategy. It's not important
        how the search is done, either serial or parallel or based on
        coroutines, as long as it returns an iterator of valid data sources,
        iterator that can be also passed again to another strategy.

        :param data_sources:
            An iterator of possible data source instances.
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

    def search_data_source(self, data_sources):
        return (source for source in data_sources
                if source.__class__.__name__ in self._names)


class SerialSearchStrategy(BaseSearchStrategy):
    """A strategy that chooses a data source in serial

    It will also return the first data source that was found.
    """

    def search_data_source(self, data_sources):
        for data_source in data_sources:
            if self.is_datasource_available(data_source):
                return iter((data_source, ))
