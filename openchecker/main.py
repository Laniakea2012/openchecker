from flask import Flask, request, jsonify
from flask_restful import Resource, Api
from flask_jwt import JWT, jwt_required, current_identity
from user_manager import authenticate, identity
from token_operator import secret_key
from datetime import timedelta
import os
from message_queue import test_rabbitmq_connection, create_queue, publish_message
from helper import read_config
import json
from typing import Dict, Any
import logging
from functools import wraps

# config logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = secret_key
# app.config['JWT_AUTH_URL_RULE'] = '/auth'
app.config['JWT_EXPIRATION_DELTA'] = timedelta(days=30)
app.config['JSON_SORT_KEYS'] = False  # keep JSON response order

api = Api(app)

jwt = JWT(app, authenticate, identity)

# read config
config = read_config('config/config.ini', "RabbitMQ")
server_config = read_config('config/config.ini', "OpenCheck")

def validate_payload(required_fields: list) -> callable:
    """Decorator to validate request payload"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({"error": "Content-Type must be application/json"}), 400
            
            payload = request.get_json()
            missing_fields = [field for field in required_fields if field not in payload]
            
            if missing_fields:
                return jsonify({
                    "error": "Missing required fields",
                    "missing_fields": missing_fields
                }), 400
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class Test(Resource):
    @jwt_required()
    def get(self):
        try:
            return jsonify({"user": current_identity})
        except Exception as e:
            logger.error(f"Error in Test GET: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    @jwt_required()
    @validate_payload(['message'])
    def post(self):
        try:
            payload = request.get_json()
            message = payload['message']
            return jsonify({"message": f"Message received: {message}, test pass!"})
        except Exception as e:
            logger.error(f"Error in Test POST: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

class OpenCheck(Resource):
    @jwt_required()
    @validate_payload(['commands', 'project_url', 'callback_url', 'task_metadata'])
    def post(self):
        try:
            payload = request.get_json()
            
            message_body = {
                "command_list": payload['commands'],
                "project_url": payload['project_url'],
                "commit_hash": payload.get("commit_hash"),
                "callback_url": payload['callback_url'],
                "task_metadata": payload['task_metadata']
            }

            pub_res = publish_message(config, "opencheck", json.dumps(message_body))
            
            if not pub_res:
                return jsonify({"error": "Failed to publish message"}), 500

            return jsonify({
                "message": "Message received, start check",
                "details": "Results will be sent to the provided callback URL"
            })
            
        except Exception as e:
            logger.error(f"Error in OpenCheck POST: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

api.add_resource(Test, '/test')
api.add_resource(OpenCheck, '/opencheck')

def init():
    """初始化应用"""
    try:
        test_rabbitmq_connection(config)
        create_queue(config, "dead_letters")
        create_queue(config, "opencheck", 
                    arguments={'x-dead-letter-exchange': '', 
                             'x-dead-letter-routing-key': 'dead_letters'})
        logger.info("Application initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise

if __name__ == '__main__':
    init()
    
    use_ssl = server_config.get("use_ssl", "false").lower() == "true"
    
    if use_ssl:
        ssl_context = (
            server_config["ssl_crt_path"],
            server_config["ssl_key_path"]
        )
        app.run(
            debug=False,
            host=server_config["host"],
            port=int(server_config["port"]),
            ssl_context=ssl_context
        )
    else:
        app.run(
            debug=False,
            host=server_config["host"],
            port=int(server_config["port"])
        )
