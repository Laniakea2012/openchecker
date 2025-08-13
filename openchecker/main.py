from flask import Flask, request
from flask_restful import Resource, Api
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from user_manager import authenticate, identity
from datetime import timedelta
import os
from message_queue import test_rabbitmq_connection, create_queue, publish_message
from helper import read_config
from logger import setup_logging, get_logger, log_performance
import json
import uuid

# Initialize logging system
setup_logging(
    log_level=os.getenv('LOG_LEVEL', 'INFO'),
    log_format=os.getenv('LOG_FORMAT', 'structured'),
    enable_console=True,
    enable_file=False,
    log_dir='logs'
)

logger = get_logger('openchecker.main')

jwt_config = read_config('config/config.ini', "JWT")
secret_key = jwt_config.get("secret_key", "your_secret_key")
expires_minutes = int(jwt_config.get("expires_minutes", 30))

app = Flask(__name__)
app.config['SECRET_KEY'] = secret_key
app.config['JWT_SECRET_KEY'] = secret_key
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=expires_minutes)

api = Api(app)

jwt = JWTManager(app)

# Authentication route
@app.route('/auth', methods=['POST'])
def auth():
    # try Basic Auth
    auth = request.authorization
    if auth and auth.username and auth.password:
        user = authenticate(auth.username, auth.password)
        if not user:
            return {"error": "Invalid credentials"}, 401
        access_token = create_access_token(identity=user.id)
        return {"access_token": access_token, "token_type": "Bearer"}
    # try JSON body
    data = request.get_json()
    if data and 'username' in data and 'password' in data:
        user = authenticate(data['username'], data['password'])
        if not user:
            return {"error": "Invalid credentials"}, 401
        access_token = create_access_token(identity=user.id)
        return {"access_token": access_token, "token_type": "Bearer"}
    return {"error": "Missing credentials"}, 401

config = read_config('config/config.ini', "RabbitMQ")

@app.before_request
def before_request():
    """Pre-request processing"""
    logger.info(f"Received request: {request.method} {request.path}", 
               extra={'extra_fields': {
                   'method': request.method,
                   'path': request.path,
                   'remote_addr': request.remote_addr,
                   'user_agent': request.headers.get('User-Agent', '')
               }})

@app.after_request
def after_request(response):
    """Post-request processing"""
    logger.info(f"Response completed: {response.status_code}", 
               extra={'extra_fields': {
                   'status_code': response.status_code,
                   'content_length': response.content_length
               }})
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return {"error": "Internal Server Error"}, 500

class Test(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = identity({'identity': user_id})
        logger.info("Test endpoint called", extra={'extra_fields': {'user_id': user_id}})
        return user

    @jwt_required()
    def post(self):
        payload = request.get_json()
        message = payload['message']

        user_id = get_jwt_identity()
        logger.info("Test POST endpoint called", 
                   extra={'extra_fields': {
                       'user_id': user_id,
                       'message': message
                   }})

        return "Message received: {}, test pass!".format(message)

class OpenCheck(Resource):
    @jwt_required()
    @log_performance('openchecker.api')
    def post(self):
        payload = request.get_json()

        #TODO  do request body check here.

        message_body = {
            "command_list": payload['commands'],
            "project_url": payload['project_url'],
            "commit_hash": payload.get("commit_hash"),
            "access_token": payload.get("access_token"),
            "callback_url": payload['callback_url'],
            "task_metadata": payload['task_metadata']
        }

        user_id = get_jwt_identity()
        logger.info("Started processing OpenCheck request", 
                   extra={'extra_fields': {
                       'user_id': user_id,
                       'project_url': payload['project_url'],
                       'commands': payload['commands'],
                       'callback_url': payload['callback_url']
                   }})

        pub_res = publish_message(config, "opencheck", json.dumps(message_body))

        logger.info("OpenCheck message published to queue", 
                   extra={'extra_fields': {
                       'publish_result': pub_res,
                       'project_url': payload['project_url']
                   }})

        return "Message received: {}, start check, the results would sent to callback_url you passed later.".format(message_body)


api.add_resource(Test, '/test')
api.add_resource(OpenCheck, '/opencheck')


# @log_performance('openchecker.init')
def init():
    """Initialize application"""
    logger.info("Starting application initialization")
    
    try:
        test_rabbitmq_connection(config)
        # logger.info("RabbitMQ connection test successful")
        
        create_queue(config, "dead_letters")
        # logger.info("Dead letter queue created successfully")
        
        create_queue(config, "opencheck", arguments={'x-dead-letter-exchange': '', 'x-dead-letter-routing-key': 'dead_letters'})
        # logger.info("Main queue created successfully")
        
        logger.info("Application initialization completed")
    except Exception as e:
        logger.error(f"Application initialization failed: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    init()

    server_config = read_config('config/config.ini', "OpenCheck")

    use_ssl = False  # Set this to True to enable SSL
    if use_ssl:
        ssl_context = (server_config["ssl_crt_path"], server_config["ssl_key_path"])
        logger.info("Starting SSL server", 
                   extra={'extra_fields': {
                       'host': server_config["host"],
                       'port': server_config["port"],
                       'ssl': True
                   }})
        app.run(debug=False, host=server_config["host"], port=int(server_config["port"]), ssl_context=ssl_context)
    else:
        logger.info("Starting HTTP server", 
                   extra={'extra_fields': {
                       'host': server_config["host"],
                       'port': server_config["port"],
                       'ssl': False
                   }})
        app.run(debug=False, host=server_config["host"], port=int(server_config["port"]))
