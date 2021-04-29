

class RedisPort:
    '''
    使用Redis代替之前的Memcached
    提供一个转换实现
    '''

    def __init__(self, redis):
        self._redis = redis

    def set(self, key, value, ttl=-1):
        pass

    def get(self, key):
        pass