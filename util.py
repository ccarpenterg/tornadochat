from copy import deepcopy
import time

class SuperDict(dict):
    def __init__(self, default):
        self.default = default

    def __getitem__(self, key):
        if key in self: return self.get(key)
        return self.setdefault(key, deepcopy(self.default))

def get_timestamp():
    clock = time.time()
    return int(clock*10**6)
