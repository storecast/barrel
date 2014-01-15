"""When I die I want to decompose in a barrel of porter and have it served in all the pubs in Dublin. J. P. Donleavy"""


class StoreMeta(type):
    """Metaclass that farms class attributes and gather the ones that are of
    type Field in the `fields` attributes.
    """
    def __new__(cls, name, parents, dct):
        fields = {}
        for k, f in dct.iteritems():
            if isinstance(f, (Field,)):
                fields[k] = f
        dct['fields'] = fields
        return super(StoreMeta, cls).__new__(cls, name, parents, dct)


def simple_get(key, dictionary):
    return dictionary[key]


def deep_get(deep_key, dictionary, sep=':'):
    """Allows to fetch through multiple dictionary levels, splitting
    the compound key using the specified separator.
    """
    keys = deep_key.split(sep)
    while keys:
        dictionary = dictionary[keys.pop(0)]
    return dictionary


class Field(object):
    """Base field class for dict datastore handling."""

    def __init__(self, target, target_sep=':'):
        self.target = target
        self.target_sep = target_sep

    def get(self, dct):
        if self.target and self.target_sep in self.target:
            return deep_get(self.target, dct, self.target_sep)
        else:
            return simple_get(self.target, dct)


class EmbeddedStoreField(Field):
    """Field that enables to embed a one or multiple dict datastores.
    By setting the target to `False`, it's also possible to create a virtual
    datastore, i.e. adding a level that doesn't exist in the datastore.
    """
    def __init__(self, target, store_class, is_array=False):
        self.store_class = store_class
        self.store = []
        if is_array:
            self.store = CollectionStore(store_class)
        else:
            self.store = store_class()
        super(EmbeddedStoreField, self).__init__(target)

    def set_store_data(self, data):
        if self.target is False:
            self.store.data = data
        else:
            self.store.data = data[self.target] if self.target in data else {}


class Store(object):
    """Base model class for dict datastore handling."""
    __metaclass__ = StoreMeta

    def __init__(self, data=None):
        if data is None:
            data = {}
        # this uses the property to set the _data attribute
        self.data = data

    def _get_data(self):
        return self._data

    def _set_data(self, data):
        self._data = data
        for f in self.fields.values():
            if isinstance(f, (EmbeddedStoreField,)):
                f.set_store_data(data)

    def _del_data(self):
        del self._data
        for f in self.fields.values():
            if isinstance(f, (EmbeddedStoreField,)):
                del f.store.data

    data = property(_get_data, _set_data, _del_data)

    def __getattribute__(self, name):
        getattr = super(Store, self).__getattribute__
        attr = getattr(name)
        if isinstance(attr, (EmbeddedStoreField,)):
            # in case of embedded store, return the store instead of the field
            return getattr('fields')[name].store
        elif isinstance(attr, (Field,)):
            # if it's a field, fetch the value in the model data and return it
            try:
                return attr.get(self.data)
            except (KeyError,):
                raise AttributeError("'%s' datastore lookup failed for '%s'" %
                    (self.__class__.__name__, attr.target))
        else:
            return attr


class CollectionStore(Store):
    """Handles collection of stores and provide array-like interface to
    access them.
    """
    def __init__(self, store_class, data=[]):
        self.store_class = store_class
        self.stores = []
        self.data = data

    def _get_data(self):
        return self._data

    def _set_data(self, data):
        self.stores = []
        for d in data:
            store = self.store_class(d)
            for f in store.fields.values():
                if isinstance(f, (EmbeddedStoreField,)):
                    f.set_store_data(data)
            self.stores.append(store)

    def _del_data(self):
        del self._data
        for store in self.stores:
            for f in store.fields.values():
                if isinstance(f, (EmbeddedStoreField,)):
                    del f.store.data
        self.stores = []

    data = property(_get_data, _set_data, _del_data)

    def __getitem__(self, i):
        return self.stores[i]

    def __len__(self):
        return len(self.stores)


class BooleanField(Field):
    """Handles the boolean values"""
    def get(self, dct):
        value = super(BooleanField, self).get(dct)
        if value == 'true':
            return True
        elif value == 'false':
            return False
        else:
            raise ValueError("Cannot convert to boolean: %s" % value)
