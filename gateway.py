import uuid
from fastapi import FastAPI, Form, Query, Request, Depends, HTTPException, Response
from fastapi.middleware import Middleware
from fastapi.responses import RedirectResponse
import httpx
from auth import verify_token

from starlette.middleware.sessions import SessionMiddleware

from keycloak_middleware import KeycloakRedirectMiddleware
from fastapi.middleware.cors import CORSMiddleware

from session_manager import session_manager
from config import settings

app = FastAPI(
    title="FastAPI API Gateway with Keycloak",
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Add your Angular app's URL here
            allow_credentials=True,  # Important for cookies and authorization
            allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
            allow_headers=["*"],  # Allow all headers
        )
    ],
)

# Add the middleware to your app
app.add_middleware(
    KeycloakRedirectMiddleware,
    keycloak_auth_url=settings.keycloak_auth_url,
    client_id=settings.client_id,
    redirect_uri=settings.redirect_uri,
    scope=settings.scope,
)

app.add_middleware(SessionMiddleware, secret_key="some-random-string", same_site="lax")

BACKEND_SERVICE_URLS = settings.backend_service_urls

# FRONTEND_SERVICE_URLS = {
#     "fe_service1": "http://localhost:4200",
# }

@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway(service: str, path: str, request: Request):
    # import pdb; pdb.set_trace()
    if service not in BACKEND_SERVICE_URLS:
        raise HTTPException(status_code=404, detail="Service not found")
    
    backend_url = f"{BACKEND_SERVICE_URLS[service]}/{path}"

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=backend_url,
            headers=request.headers.raw,
            content=await request.body()
        )

    return response.json()


@app.get("/login")
async def login(request: Request, response: Response, code: str = Query(...)):
    try:
        # token_url = "http://keycloak:8080/realms/fastapi-gateway/protocol/openid-connect/token"
        token_url = settings.keycloak_token_url
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.client_id,
                    "code": code,
                    "redirect_uri": settings.redirect_uri, # should be same as keycloak client valid redirect url
                   "client_secret": settings.client_secret #Replace with your client secret if required by Keycloak configuration
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            token_response.raise_for_status()
            token_data = token_response.json()

            access_token = token_data["access_token"]
            refresh_token = token_data["refresh_token"]

            session_id = session_manager.create_session(access_token, refresh_token)

            request.session['session_id'] = session_id

            # response.set_cookie('session_id', session_id, httponly=True, domain="http://localhost:4200", path="/restaurants")
            return RedirectResponse(url=settings.ui_home_url)

    except httpx.HTTPError as e:
        print(f"Keycloak Authentication failed: {e}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")
    except KeyError as e:
        print(f"Invalid Keycloak response: Missing key {e}")
        raise HTTPException(status_code=500, detail="Invalid Keycloak response")
    except Exception as e:
        print(f"Unexpected error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
