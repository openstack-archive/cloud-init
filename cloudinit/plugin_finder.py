# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

"""Various base classes and implementations for finding *plugins*."""

import abc
import logging
import pkgutil

import six

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseModuleIterator(object):
    """Base class for describing a *module iterator*

    A module iterator is a class that's capable of listing
    modules or packages from a specific location, which are
    already loaded.
    """

    def __init__(self, search_paths):
        self._search_paths = search_paths

    @abc.abstractmethod
    def list_modules(self):
        """List all the modules that this finder knows about."""


class PkgutilModuleIterator(BaseModuleIterator):
    """A class based on the *pkgutil* module for discovering modules."""

    @staticmethod
    def _find_module(finder, module):
        """Delegate to the *finder* for finding the given module."""
        return finder.find_module(module).load_module(module)

    def list_modules(self):
        """List all modules that this class knows about."""
        for finder, name, _ in pkgutil.walk_packages(self._search_paths):
            try:
                module = self._find_module(finder, name)
            except ImportError:
                LOG.debug('Could not import the module %r using the '
                          'search paths %r', name, finder.path)
                continue

            yield module
