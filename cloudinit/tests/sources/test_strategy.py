# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

from cloudinit.sources import strategy
from cloudinit import tests
from cloudinit.tests.util import mock


class TestStrategy(tests.TestCase):

    def test_custom_strategy(self):
        class CustomStrategy(strategy.BaseSearchStrategy):

            def search_data_sources(self, data_sources):
                # Return them in reverse order
                return list(reversed(data_sources))

        data_sources = [mock.sentinel.first, mock.sentinel.second]
        instance = CustomStrategy()
        sources = instance.search_data_sources(data_sources)

        self.assertEqual(sources, [mock.sentinel.second, mock.sentinel.first])

    def test_is_datasource_available(self):
        class CustomStrategy(strategy.BaseSearchStrategy):
            def search_data_sources(self, _):
                pass

        instance = CustomStrategy()
        good_source = mock.Mock()
        good_source.load.return_value = True
        bad_source = mock.Mock()
        bad_source.load.return_value = False

        self.assertTrue(instance.is_datasource_available(good_source))
        self.assertFalse(instance.is_datasource_available(bad_source))

    def test_filter_name_strategy(self):
        names = ['first', 'second', 'third']
        full_names = names + ['fourth', 'fifth']
        sources = [type(name, (object, ), {})() for name in full_names]
        instance = strategy.FilterNameStrategy(names)

        sources = list(instance.search_data_sources(sources))

        self.assertEqual(len(sources), 3)
        self.assertEqual([source.__class__.__name__ for source in sources],
                         names)

    def test_serial_search_strategy(self):
        def is_available(self, data_source):
            return data_source in available_sources

        sources = [mock.sentinel.first, mock.sentinel.second,
                   mock.sentinel.third, mock.sentinel.fourth]
        available_sources = [mock.sentinel.second, mock.sentinel.fourth]

        with mock.patch('cloudinit.sources.strategy.BaseSearchStrategy.'
                        'is_datasource_available', new=is_available):
            instance = strategy.SerialSearchStrategy()
            valid_sources = list(instance.search_data_sources(sources))

        self.assertEqual(available_sources, valid_sources)
