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
class BaseModuleFinder(object):
    """Base class for describing a *module finder*

    A module finder is a class that's capable of listing
    modules or packages for a specific location, as well as
    loading a module.
    """

    def __init__(self, search_paths):
        self._search_paths = search_paths

    @abc.abstractmethod
    def find_module(self, finder, name):
        """Try to load the given module *name* using the given *finder*."""

    @abc.abstractmethod
    def list_all_modules(self):
        """List all the modules that this finder knows about."""

    @abc.abstractmethod
    def list_valid_modules(self):
        """List all the modules that are valid for this finder

        Valid modules can be modules that exports a specific API,
        for instance, as in the context of plugins.
        """


class ModuleFinder(BaseModuleFinder):
    """A finder based on the *pkgutil* module for discovering modules."""

    @staticmethod
    def find_module(finder, module):
        """Delegate to the *finder* for finding the given module."""
        return finder.find_module(module).load_module(module)

    def list_all_modules(self):
        """List all modules that this finder knows about."""
        for finder, name, ispkg in pkgutil.walk_packages(self._search_paths):
            try:
                module = self.find_module(finder, name)
            except ImportError:
                LOG.debug('Could not import the module %r using the '
                          'search paths %r', name, finder.path)
                continue

            yield finder, name, module
