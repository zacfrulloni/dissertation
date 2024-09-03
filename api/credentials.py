from fastapi import APIRouter, HTTPException, Request
from app.config import config, set_api_keys
from pydantic import BaseModel

router = APIRouter()

class ApiCredentials(BaseModel):
    langchain_api_key: str
    google_maps_api_key: str
    openai_api_key: str

@router.post("/set-credentials")
async def set_credentials(credentials: ApiCredentials):
    set_api_keys({
        # "langchain_api_key": null,
        # "google_maps_api_key": null,

        "langchain_api_key": credentials.langchain_api_key,
        "google_maps_api_key": credentials.google_maps_api_key,
        "openai_api_key": credentials.openai_api_key
        } )

    return {"message": "credentials have been updated "}