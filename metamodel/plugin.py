class PluginMeta(type):
    # we use __init__ rather than __new__ here because we want
    # to modify attributes of the class *after* they have been
    # created
    def __init__(cls, name, bases, dct):
        if not hasattr(cls, 'registry'):
            # this is the base class.  Create an empty registry
            cls.registry = {}
        else:
            # this is a derived class.  Add cls to the registry
            interface_id = name.lower()
            cls.registry[interface_id] = cls

        super(PluginMeta, cls).__init__(name, bases, dct)


class Plugin(object):
    registry = {}

    @classmethod
    def on_instance_model_detail_view(cls, instance_model):
        pass

    __metaclass__ = PluginMeta
