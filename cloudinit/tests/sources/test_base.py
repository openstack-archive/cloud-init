# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import functools
import string
import types

from cloudinit import exceptions
from cloudinit import plugin_finder
from cloudinit.sources import base
from cloudinit.sources import strategy
from cloudinit import tests


class TestDataSourceDiscovery(tests.TestCase):

    def setUp(self):
        super(TestDataSourceDiscovery, self).setUp()
        self._modules = None

    @property
    def modules(self):
        if self._modules:
            return self._modules

        class Module(types.ModuleType):
            def data_sources(self):
                return (self, )

            def __call__(self):
                return self

            @property
            def __class__(self):
                return self

        modules = self._modules = list(map(Module, string.ascii_letters))
        return modules

    @property
    def module_iterator(self):
        modules = self.modules

        class ModuleIterator(plugin_finder.BaseModuleIterator):
            def list_modules(self):
                return modules + [None, "", 42]

        return ModuleIterator(None)

    def test_loader_api(self):
        # Test that the API of DataSourceLoader is sane
        loader = base.DataSourceLoader(
            names=[], module_iterator=self.module_iterator,
            strategies=[])

        all_data_sources = list(loader.all_data_sources())
        valid_data_sources = list(loader.valid_data_sources())

        self.assertEqual(all_data_sources, self.modules)
        self.assertEqual(valid_data_sources, self.modules)

    def test_loader_strategies(self):
        class OrdStrategy(strategy.BaseSearchStrategy):
            def search_data_sources(self, data_sources):
                return filter(lambda source: ord(source.__name__) < 100,
                              data_sources)

        class NameStrategy(strategy.BaseSearchStrategy):
            def search_data_sources(self, data_sources):
                return (source for source in data_sources
                        if source.__name__ in ('a', 'b', 'c'))

        loader = base.DataSourceLoader(
            names=[], module_iterator=self.module_iterator,
            strategies=(OrdStrategy(), NameStrategy(), ))
        valid_data_sources = list(loader.valid_data_sources())

        self.assertEqual(len(valid_data_sources), 3)
        self.assertEqual([source.__name__ for source in valid_data_sources],
                         ['a', 'b', 'c'])

    def test_get_data_source_filtered_by_name(self):
        source = base.get_data_source(
            names=['a', 'c'],
            module_iterator=self.module_iterator.__class__)
        self.assertEqual(source.__name__, 'a')

    def test_get_data_source_multiple_strategies(self):
        class ReversedStrategy(strategy.BaseSearchStrategy):
            def search_data_sources(self, data_sources):
                return reversed(list(data_sources))

        source = base.get_data_source(
            names=['a', 'b', 'c'],
            module_iterator=self.module_iterator.__class__,
            strategies=(ReversedStrategy, ))

        self.assertEqual(source.__name__, 'c')

    def test_get_data_source_no_data_source(self):
        get_data_source = functools.partial(
            base.get_data_source,
            names=['totallymissing'],
            module_iterator=self.module_iterator.__class__)

        exc = self.assertRaises(exceptions.CloudInitError,
                                get_data_source)
        self.assertEqual(str(exc), 'No available data source found')

    def test_get_data_source_no_name_filtering(self):
        source = base.get_data_source(
            names=[], module_iterator=self.module_iterator.__class__)
        self.assertEqual(source.__name__, 'a')
