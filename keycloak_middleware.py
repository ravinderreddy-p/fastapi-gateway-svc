from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from auth import verify_token

class KeycloakRedirectMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, keycloak_auth_url: str, client_id: str, redirect_uri: str, scope: str):
        super().__init__(app)
        self.keycloak_auth_url = keycloak_auth_url
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.scope = scope

    async def dispatch(self, request: Request, call_next):
        #Check if the url is login or login-token, to prevent infinite loop
        if request.url.path in ["/home"]:
            return await call_next(request)
            

        # Check if an access token is present
        try:
            user = await verify_token(request)
            # If the token is valid, let the request proceed
            return await call_next(request)
        except HTTPException as e:
            if e.status_code == 403:
                #If the token is not valid, redirect to Keycloak
                 # Redirect to Keycloak for login
                auth_url = f"{self.keycloak_auth_url}?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&scope={self.scope}"
                return RedirectResponse(url=auth_url)
            else:
                raise e # rethrow http exception if it is not 401
            