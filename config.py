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
    backend_service_urls: dict = {"service1": "http://service1:8001", "service2": "http://service2:8002"}
    front_service_urls: dict = {"ui": "http://ui:80"}
    # front_service_urls: dict = {"ui": "http://localhost:8081"}
    database_url: str
    ui_home_url: str = "http://localhost:8000/ui/restaurants"


    class Config:
        env_file = ".env"  #optional, if you have a .env file for local development
        env_file_encoding = "utf-8"

settings = Settings()
