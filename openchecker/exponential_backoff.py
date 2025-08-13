import random
import time
import requests, urllib3
from helper import read_config
from openai import OpenAI
import os

file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(file_dir)
config_file = os.path.join(project_root, "config", "config.ini")
chatbot_config = read_config(config_file, "ChatBot")

# define a retry decorator
def retry_with_exponential_backoff(
    func,
    initial_delay: float = 1,
    exponential_base: float = 2,
    jitter: bool = True,
    max_retries: int = 3,
    errors: tuple = ( requests.exceptions.RequestException,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.HTTPError,
                    urllib3.exceptions.NewConnectionError)
    ):
    """Retry a function with exponential backoff."""
 
    def wrapper(*args, **kwargs):
        # Initialize variables
        num_retries = 0
        delay = initial_delay
 
        # Loop until a successful response or max_retries is hit or an exception is raised
        while True:
            try:
                return func(*args, **kwargs)
 
            # Retry on specific errors
            except errors as e:
                # Increment retries
                num_retries += 1
 
                # Check if max retries has been reached
                if num_retries > max_retries:
                    raise Exception(
                        f"Maximum number of retries ({max_retries}) exceeded."
                    )
 
                # Increment the delay
                delay *= exponential_base * (1 + jitter * random.random())
 
                # Sleep for the delay
                time.sleep(delay)
 
            # Raise exceptions for any errors not specified
            except Exception as e:
                raise e
 
    return wrapper
    
@retry_with_exponential_backoff
def post_with_backoff(**kwargs):
    return requests.post(**kwargs)

@retry_with_exponential_backoff
def completion_with_backoff(**kwargs):
    # chatbot_config = read_config('config/config.ini', "ChatBot")

    client = OpenAI(
        api_key = chatbot_config["api_key"],
        base_url = chatbot_config["base_url"]
    )

    # chat_completion = client.chat.completions.create(model=model, messages=messages)
    chat_completion = client.chat.completions.create(model=chatbot_config["model_name"] ,**kwargs)

    return chat_completion.choices[0].message.content