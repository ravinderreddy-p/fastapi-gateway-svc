import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    keycloak_url: str
    keycloak_auth_url: str
    keycloak_token_url: str
    client_id: str
    client_secret: str | None = None
    redirect_uri: str
    scope: str
    backend_service_urls: dict = {"service1": "http://service1:8001", "service2": "http://service2:8002"}
    # front_service_urls: dict = {"ui": "http://ui:80"}
    front_service_urls: dict = {"ui": "http://localhost:8081"}
    database_url: str
    ui_home_url: str = "http://localhost:8000/ui/restaurants"
    tenant_config: dict = {"tenant1": "tenant1", "tenant2":"tenant2"}

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    
    def load_tenant_config(self, tenant: str) -> None:
        prefix = f"TENANT_{tenant.upper()}_"
        
        self.keycloak_url = os.getenv(f"{prefix}KEYCLOAK_URL")
        self.keycloak_auth_url = os.getenv(f"{prefix}KEYCLOAK_AUTH_URL")
        self.keycloak_token_url = os.getenv(f"{prefix}KEYCLOAK_TOKEN_URL")
        self.client_id = os.getenv(f"{prefix}CLIENT_ID")
        self.client_secret = os.getenv(f"{prefix}CLIENT_SECRET")
        self.redirect_uri = os.getenv(f"{prefix}REDIRECT_URI")
        self.scope = os.getenv(f"{prefix}SCOPE")
        # self.database_url = os.getenv(f"{prefix}DATABASE_URL")
        self.ui_home_url = os.getenv(f"{prefix}UI_HOME_URL")
        

settings = Settings()
