import hashlib
import hmac
import time
from urllib.parse import quote
from logger import get_logger

logger = get_logger('openchecker.aksk.signer')

class Signer:
    @staticmethod
    def sign(request):
        try:
            signed_headers = Signer.build_signed_headers(request)
            body_hash = Signer.calculate_body_hash(request)
            timestamp = Signer.build_timestamp(request)
            canonical_request = Signer.create_canonical_request(request, timestamp, signed_headers, body_hash)
            sign_value = Signer.sign_key(canonical_request, request.get_secret_key())
            return Signer.build_authorization_header(request, timestamp, signed_headers, sign_value)
        except Exception as e:
            logger.error(f"Error during signing process: {e}")
            return None
    
    @staticmethod
    def get_timestamp(authorization):
        timestamp = Signer.get_authorization_field(authorization, "timestamp=")
        if not timestamp:
            return None
        try:
            return int(timestamp)
        except ValueError:
            logger.error("Invalid timestamp format in authorization header")
            return None
    
    @staticmethod
    def get_access_id(authorization):
        return Signer.get_authorization_field(authorization, "access_id=")
    
    @staticmethod
    def build_timestamp(request):
        if request.get_timestamp() and request.get_timestamp().strip():
            return request.get_timestamp()
        return str(int(time.time() * 1000))

    @staticmethod
    def build_signed_headers(request):
        sorted_header = sorted(request.get_headers().keys(), key=str.lower)
        return ";".join(header.lower() for header in sorted_header)

    @staticmethod
    def get_signed_headers(authorization):
        signed_headers = Signer.get_authorization_field(authorization, "signedHeaders=")
        return signed_headers.split(";") if signed_headers else []

    @staticmethod
    def get_contain_path(authorization):
        is_contain_path = Signer.get_authorization_field(authorization, "containPath=")
        return True if not is_contain_path else is_contain_path.lower() == "true"

    @staticmethod
    def get_contain_body(authorization):
        is_contain_body = Signer.get_authorization_field(authorization, "containBody=")
        return True if not is_contain_body else is_contain_body.lower() == "true"

    @staticmethod
    def get_contain_query(authorization):
        is_contain_query = Signer.get_authorization_field(authorization, "containQuery=")
        return True if not is_contain_query else is_contain_query.lower() == "true"

    @staticmethod
    def calculate_body_hash(request):
        body = request.get_body() 
        return Signer.hash(body) if body and body.strip() and request.is_contain_body() else ""

    @staticmethod
    def create_canonical_request(request, timestamp, signed_headers, body_hash):
        canonical_request = []
        if not request.is_contain_path():
            canonical_request.append(str(request.is_contain_path()))
        if not request.is_contain_body():
            canonical_request.append(str(request.is_contain_body()))
        if not request.is_contain_query():
            canonical_request.append(str(request.is_contain_query()))
        canonical_request.extend([
            timestamp,
            request.get_method().upper() if request.get_method() else "",
            Signer.build_canonical_path(request),
            Signer.build_canonical_query(request),
            Signer.build_canonical_header(request),
            signed_headers,
            body_hash
        ])
        return "\n".join(canonical_request)

    @staticmethod
    def build_canonical_path(request):
        if not request.is_contain_path():
            return ""
        path = request.get_path() or "/"
        if not path.startswith("/"):
            path = "/" + path
        if path.endswith("/"):
            path = path[:-1]
        return path

    @staticmethod
    def build_canonical_query(request):
        if not request.is_contain_query():
            return ""
        sorted_params = sorted(request.get_query_params().keys(), key=str.lower)
        query_return = "".join(f"{param}={request.get_query_params()[param]}" for param in sorted_params)
        encoded_query = quote(query_return, safe="=")
        encoded_query = encoded_query + "&"
        return encoded_query
    
    @staticmethod
    def build_canonical_header(request):
        sorted_headers = sorted(request.get_headers().keys(), key=str.lower)
        return "\n".join(f"{header.lower()}:{request.get_headers()[header].strip() if request.get_headers()[header] else ''}" for header in sorted_headers)
    
    @staticmethod
    def build_authorization_header(request, timestamp, signed_headers, sign_value):
        auth_header = ["SDK-HMAC-SHA256"]
        if not request.is_contain_path():
            auth_header.append(f"containPath={request.is_contain_path()}")
        if not request.is_contain_body():
            auth_header.append(f"containBody={request.is_contain_body()}")
        if not request.is_contain_query():
            auth_header.append(f"containQuery={request.is_contain_query()}")
        auth_header.extend([
            f"accessId={request.get_access_id()}",
            f"timestamp={timestamp}",
            f"signedHeaders={signed_headers}",
            f"signature={sign_value}"
        ])
        auth_header_str = ",".join(auth_header)
        return auth_header_str.replace(",", " ", 1)
    
    @staticmethod
    def hash(value):
        sha256 = hashlib.sha256()
        sha256.update(value.encode('utf-8'))
        return sha256.hexdigest()   

    @staticmethod
    def sign_key(data, secret_key):
        data_bytes = data.encode('utf-8')
        secret_key_bytes = secret_key.encode('utf-8')
        hmac_data = hmac.new(secret_key_bytes, data_bytes, hashlib.sha256).digest()
        return hmac_data.hex()

    @staticmethod
    def get_authorization_field(authorization, field_name):
        if not authorization or not authorization.strip():
            raise Warning("The authorization is error")
        pos = authorization.find(field_name)
        if pos == -1:
            return ""
        result = authorization[pos + len(field_name):]
        pos = result.find(",")
        if pos == -1:
            return ""
        return result[:pos]