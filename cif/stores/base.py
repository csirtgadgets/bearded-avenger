
class Store(object):

    name = 'base'

    def __init__(self):
        pass

    def auth(self, token):
        return self.auth_read(token)

    def auth_read(self, token):
        pass

    def auth_write(self, token):
        pass

    def search(self, data):
        pass

    def submit(self, data):
        pass