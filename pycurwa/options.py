from collections import namedtuple


class Options(dict):
    def __init__(self, iterable=None, **kwargs):
        super(Options, self).__init__(iterable, **kwargs)
        
    def interface(self):
        interface = self.get('interface')
        return interface if interface.lower() != 'none' else None
    
    def proxy(self):
        proxy = self.get('proxies')
        if proxy:
            auth = Auth(proxy['username'], proxy['password']) if proxy['username'] else None

            proxy = Proxy(proxy['type'], str(proxy['address']), proxy['port'], auth)
            return proxy
        
    def ipv6_enabled(self):
        return bool(self.get('ipv6'))

    def auth(self):
        return str(self.get('auth'))
    
    def timeout(self):
        return int(self.get('timeout'))


class Auth(namedtuple('Auth', ['user', 'password'])):
    def __new__(cls, user, password):
        return super(Auth, cls).__new__(cls, user, password)


class Proxy(namedtuple('Proxy', ['type', 'address', 'port', 'auth'])):

    def __new__(cls, proxy_type, address, port, auth=None):
        return super(Proxy, cls).__new__(cls, proxy_type, address, port, auth)