import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    keycloak_url: str
    keycloak_auth_url: str
    keycloak_token_url: str
    client_id: str
    client_secret: str | None = None
    redirect_uri: str
    scope: str
    backend_service_urls: dict
    database_url: str
    ui_home_url: str

    class Config:
        env_file = ".env"  #optional, if you have a .env file for local development
        env_file_encoding = "utf-8"

settings = Settings()
