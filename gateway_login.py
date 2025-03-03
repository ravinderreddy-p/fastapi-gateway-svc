from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient, HTTPError
from typing import Optional
from urllib.parse import urlencode
import os
from auth import verify_token
from jose import JWTError, jwt
from jose.constants import ALGORITHMS
import asyncio

app = FastAPI(
    title="FastAPI API Gateway",
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:4200"],  # Update with your Angular app's URL
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ],
)

# Load environment variables
# Load environment variables (replace with your actual environment variable setup)
PORT = int(os.environ.get("PORT", 8000))
KEYCLOAK_AUTH_URL = os.environ.get("KEYCLOAK_AUTH_URL", "http://localhost:8080/realms/fastapi-gateway/protocol/openid-connect/auth")
KEYCLOAK_TOKEN_URL = os.environ.get("KEYCLOAK_TOKEN_URL", "http://localhost:8080/realms/fastapi-gateway/protocol/openid-connect/token")
CLIENT_ID = os.environ.get("CLIENT_ID", "fastapi-client")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("REDIRECT_URI", "http://localhost:8000/callback")
ANGULAR_APP_URL = os.environ.get("ANGULAR_APP_URL", "http://localhost:4200")
FASTAPI_BACKEND_URL = os.environ.get("FASTAPI_BACKEND_URL", "http://localhost:8001")
KEYCLOAK_USER_INFO = os.environ.get("KEYCLOAK_USER_INFO", "http://localhost:8080/realms/fastapi-gateway/protocol/openid-connect/userinfo")
ALGORITHM = ALGORITHMS.RS256
JWKS_URL = f"{os.environ.get('KEYCLOAK_URL', 'http://localhost:8080/realms/fastapi-gateway')}/protocol/openid-connect/certs"


async def get_jwks():
    async with AsyncClient() as client:
        response = await client.get(JWKS_URL)
        return response.json()

async def verify_token_from_cookie(request: Request) -> Optional[dict]:
    """
    Verifies the access token from the cookie.
    Returns the payload if valid, otherwise returns None.
    """
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        header = jwt.get_unverified_header(token)
        jwks = await get_jwks()
        key = next(
            (key for key in jwks["keys"] if key["kid"] == header["kid"]), None
        )
        if not key:
             raise HTTPException(status_code=403, detail="Invalid token")
        public_key = jwt.jwk_from_dict(key)
        payload = jwt.decode(token, public_key, algorithms=[ALGORITHM], audience="account")
        return payload
    except JWTError as e:
        return None



@app.get("/")
async def root(request: Request):
    """
    Checks for an authentication token in cookies.
    If absent, the user is redirected to Keycloak for login.
    Otherwise, the user is redirected to the UI.
    """
    payload = await verify_token_from_cookie(request)
    if not payload:
        auth_url = f"{KEYCLOAK_AUTH_URL}?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=openid"
        return RedirectResponse(url=auth_url)

    return RedirectResponse(url=ANGULAR_APP_URL)


@app.get("/callback")
async def callback(request: Request, code: Optional[str] = None):
    """
    Keycloak will redirect back to this URL after successful authentication.
    This route exchanges the authorization code for an access token,
    stores it in an httpOnly cookie, and then redirects the user to the UI.
    """
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code missing")

    try:
        async with AsyncClient() as client:
            token_response = await client.post(
                KEYCLOAK_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": REDIRECT_URI,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            token_response.raise_for_status()
            access_token = token_response.json()["access_token"]

            # Set the token in a secure, httpOnly cookie
            response = RedirectResponse(url=ANGULAR_APP_URL)
            response.set_cookie(
                key="access_token", value=access_token, httponly=True, secure=True
            )
            return response
    except HTTPError as error:
        print(f"Error exchanging code for token: {error.response.json() if error.response else error}")
        raise HTTPException(status_code=500, detail="Authentication failed")


async def authenticate_token(request: Request):
    """
    Middleware to protect API routes.
    Verifies the token in the cookie, otherwise raises an error.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        async with AsyncClient() as client:
            response = await client.get(KEYCLOAK_USER_INFO, headers={"Authorization": f"Bearer {token}"})
            response.raise_for_status()
            user_info = response.json()
            # Add user info to the request state for later use if needed.
            # request.state.user = user_info
            return user_info  # can be used as a dependency injection result
    except HTTPError as err:
        print(err)
        raise HTTPException(status_code=403, detail="Invalid token")

@app.get("/api/backend/{path:path}")
async def proxy_to_backend(request: Request, path: str, user_info = Depends(authenticate_token)):
    """
    Proxy requests to the FastAPI backend.
    """
    # user_info = request.state.user
    token = request.cookies.get("access_token")
    backend_url = f"{FASTAPI_BACKEND_URL}/{path}"
    try:
        async with AsyncClient() as client:
          
            proxy_response = await client.request(
                method=request.method,
                url=backend_url,
                headers={**request.headers, "Authorization": f"Bearer {token}"},  # Forward headers and add Authorization
                data=await request.body()
            )
            return Response(content=proxy_response.content, status_code=proxy_response.status_code, headers=proxy_response.headers)
    except Exception as e:
        print(f"Error in proxying to backend: {e}")
        raise HTTPException(status_code=500, detail="Proxy to backend failed")

@app.get("/logout")
async def logout(request: Request):
    """
    Clears the authentication cookie and redirects the user to Keycloak's logout,
    then back to the UI.
    """
    response = RedirectResponse(
        url=f"{KEYCLOAK_AUTH_URL.replace('/auth','/logout')}?redirect_uri={ANGULAR_APP_URL}"
    )
    response.delete_cookie("access_token")
    return response
