

class BrowsableItem(object):
    """
    Maps for the template browse-list.
    """

    def __init__(self, item, *args, **kwargs):
        self._item = item
        super(BrowsableItem, self).__init__()

    @property
    def title(self):
        pass

    @property
    def link(self):
        pass

    @property
    def hint(self):
        pass

    @property
    def destructive(self):
        pass
