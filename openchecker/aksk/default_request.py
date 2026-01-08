from urllib.parse import quote, unquote

class DefaultRequest:
    def __init__(self, access_id: str, secret_key: str):
        self.access_id = access_id
        self.secret_key = secret_key
        self.method = None
        self.path = None
        self.body = None
        self.timestamp = None
        self.headers = {}
        self.query_params = {}
        self.contain_body = True
        self.contain_path = True
        self.contain_query = True
    
    def set_method(self, method: str):
        if not method:
            raise Warning("method cannot be empty")
        http_methods = method.upper()
        if http_methods not in ["GET", "POST", "PUT", "DELETE"]:
            raise Warning("method must be one of GET, POST, PUT, DELETE")
        self.method = http_methods
    
    def get_method(self) -> str:
        return self.method

    def add_header(self, name: str, value: str):
        if not name:
            raise Warning("header name cannot be empty")
        self.headers[name.lower()] = value
    
    def get_headers(self) -> dict:
        return self.headers

    def get_path(self) -> str:
        return self.path
    
    def get_url(self) -> str:
        url = self.path
        if self.query_params :
            url += '?' + '&'.join(f"{k}={v}" for k, v in self.query_params.items())
        return url

    def set_url(self, url: str):
        if not url or not url.strip():
            raise Warning("url cannot be empty")
        self.path = url
        if '?' in url:
            query_list = url.split('?', 1)
            for param in query_list:
                if '=' in param.split('&'):
                    key, value = param.split('=', 1)
                    self.query_params[quote(unquote(key))] = quote(unquote(value))

    def add_query_param(self, key: str, value: str):
        if not key or not key.strip():
            raise Warning("query parameter name cannot be empty")
        self.query_params[quote(key)] = quote(value)
    
    def get_query_params(self) -> dict:
        return self.query_params

    def set_body(self, body: str):
        self.body = body
    
    def get_body(self) -> str:
        return self.body
    
    def get_access_id(self) -> str:
        return self.access_id

    def get_secret_key(self) -> str:
        return self.secret_key
    
    def get_timestamp(self) -> str:
        return self.timestamp
    
    def set_timestamp(self, timestamp: str):
        self.timestamp = timestamp
    
    def is_contain_body(self) -> bool:
        return self.contain_body
    
    def set_contain_body(self, contain: bool):
        self.contain_body = contain
    
    def is_contain_path(self) -> bool:
        return self.contain_path
    
    def set_contain_path(self, contain: bool):
        self.contain_path = contain

    def is_contain_query(self) -> bool:
        return self.contain_query
    
    def set_contain_query(self, contain: bool):
        self.contain_query = contain
