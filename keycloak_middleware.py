from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from auth import verify_token
from session_manager import session_manager

class KeycloakRedirectMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, keycloak_auth_url: str, client_id: str, redirect_uri: str, scope: str):
        super().__init__(app)
        self.keycloak_auth_url = keycloak_auth_url
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.scope = scope

    async def dispatch(self, request: Request, call_next):
        #Check if the url is login or login-token, to prevent infinite loop
        if request.url.path in ["/login"]:
            return await call_next(request)
            

        # Check if an access token is present
        try:
            session_id = request.session.get('session_id')
            # import pdb; pdb.set_trace()
            token_data = {}
            if session_id:
                token_data = session_manager.get_session(session_id)
                if token_data:
                    token = token_data.get("access_token")
            
                    user = await verify_token(token=token)
                    # If the token is valid, let the request proceed
                    # import pdb; pdb.set_trace()
                    return await call_next(request)
                
            auth_url = f"{self.keycloak_auth_url}?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&scope={self.scope}"
            return RedirectResponse(url=auth_url)
        except HTTPException as e:
            if e.status_code == 403 or e.status_code == 401:
                #If the token is not valid, redirect to Keycloak
                 # Redirect to Keycloak for login
                auth_url = f"{self.keycloak_auth_url}?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&scope={self.scope}"
                return RedirectResponse(url=auth_url)
            else:
                raise e # rethrow http exception if it is not 401
            