from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from auth import verify_token
from session_manager import session_manager

from logger import logger
from config import Settings

request_path = {}

class KeycloakRedirectMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        logger.info(f"Request redirected for Keycloak authentication {request.url.path}")
        #Check if the url is login or login-token, to prevent infinite loop
        if request.url.path in ["/login"]:
            return await call_next(request)
        
        # Get settings from request.state
        settings: Settings = request.state.settings

        # Check if an access token is present
        try:
            session_id = request.session.get('session_id')
            if session_id:
                logger.info(f"Session ID found: {session_id}, getting the token from session manager")
                token_data = session_manager.get_session(session_id)
                if token_data:
                    token = token_data.get("access_token")
            
                    user = await verify_token(token=token, settings=settings) # Pass settings here
                    # If the token is valid, let the request proceed
                    logger.info(f"Existing Token verified successfully, proceeding with the request")
                    return await call_next(request)
                
            request_path['original_path'] = request.url.path   
            
            auth_url = f"{settings.keycloak_auth_url}?client_id={settings.client_id}&redirect_uri={settings.redirect_uri}&response_type=code&scope={settings.scope}"
            return RedirectResponse(url=auth_url)
        except HTTPException as e:
            logger.error(f"keycloack module - error occured while verifying token {e} ")
            if e.status_code == 403 or e.status_code == 401:
                #If the token is not valid, redirect to Keycloak
                 # Redirect to Keycloak for login
                auth_url = f"{settings.keycloak_auth_url}?client_id={settings.client_id}&redirect_uri={settings.redirect_uri}&response_type=code&scope={settings.scope}"
                return RedirectResponse(url=auth_url)
            else:
                raise e # rethrow http exception if it is not 401
