from cloudinit.registry import Registry
from cloudinit.tests import TestCase
from cloudinit.tests.util import mock


class TestRegistry(TestCase):

    def test_added_item_included_in_output(self):
        registry = Registry()
        item_to_register = mock.Mock()
        registry.register_item(item_to_register)
        self.assertEqual([item_to_register], registry.registered_items)

    def test_registry_starts_out_empty(self):
        self.assertEqual([], Registry().registered_items)

    def test_modifying_registered_items_isnt_exposed_to_other_callers(self):
        registry = Registry()
        registry.registered_items.append(mock.Mock())
        self.assertEqual([], registry.registered_items)
