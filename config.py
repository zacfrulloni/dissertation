import os
import dotenv
from dotenv import load_dotenv

load_dotenv()
config = {
    # "langchain_api_key": null,
    "langchain_api_key": None,
    "google_maps_api_key": None,
    "openai_api_key": None,
    "postman_api_key": os.getenv("POSTMAN_API_KEY"),
    "forked_uid": os.getenv("FORKED_UID"),
    "langchain_endpoint": os.getenv("LANGCHAIN_ENDPOINT"),
    "langchain_project": os.getenv("LANGCHAIN_PROJECT")
}


print(config)
def set_api_keys(keys):
    for key, value in keys.items():
        if key in config:
            config[key] = value