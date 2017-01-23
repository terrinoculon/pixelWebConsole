class Iter(object):
    def __init__(self) -> object:
        self.val = 0

    def __del__(self):
        self.val=0

    def next(self):
        self.val=self.val+1
        print(self.val)
        return self.val
