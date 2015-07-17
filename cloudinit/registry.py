import copy


class Registry(object):
    """A simple registry."""

    def __init__(self):
        self._items = []

    def register_item(self, item):
        """Add item to the registry."""
        self._items.append(item)

    @property
    def registered_items(self):
        """All the items that have been registered.

        This cannot be used to modify the contents of the registry.
        """
        return copy.copy(self._items)
