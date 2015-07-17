import copy


class _Registry(object):

    @property
    def registered_items(self):
        """All the items that have been registered.

        This cannot be used to modify the contents of the registry.
        """
        return copy.copy(self._items)


class ListRegistry(_Registry):
    """A simple registry for a list of objects."""

    def __init__(self):
        self._items = []

    def register_item(self, item):
        """Add item to the registry."""
        self._items.append(item)


class DictRegistry(_Registry):
    """A simple registry for a mapping of objects."""

    def __init__(self):
        self._items = {}

    def register_item(self, key, item):
        """Add item to the registry."""
        if key in self._items:
            raise ValueError(
                'Item already registered with key {0}'.format(key))
        self._items[key] = item
