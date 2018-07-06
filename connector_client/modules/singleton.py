if __name__ == '__main__':
    exit('Please use "client.py"')


class Singleton(type):
    """
    Subclass this class for singleton behavior
    """
    _instances = dict()
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class SimpleSingleton:
    """
    Classes inheriting from abstract classes subclass this class for singleton behavior
    """
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance
