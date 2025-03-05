from fastapi import FastAPI, Form, Query, Request, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
import httpx
from auth import verify_token

from keycloak_middleware import KeycloakRedirectMiddleware

app = FastAPI(title="FastAPI API Gateway with Keycloak")


# Configuration (Move this to a config file later if you want)
KEYCLOAK_AUTH_URL = "http://localhost:8080/realms/fastapi-gateway/protocol/openid-connect/auth"
CLIENT_ID = "fastapi-client"
REDIRECT_URI = "http://localhost:8000/login"
SCOPE = "openid"

# Add the middleware to your app
app.add_middleware(
    KeycloakRedirectMiddleware,
    keycloak_auth_url=KEYCLOAK_AUTH_URL,
    client_id=CLIENT_ID,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
)

BACKEND_SERVICE_URLS = {
    "service1": "http://localhost:8001",
    "service2": "http://service2:8002",
}

FRONTEND_SERVICE_URLS = {
    "fe_service1": "http://localhost:4200",
}

@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway(service: str, path: str, request: Request, user: dict = Depends(verify_token)):
    if service not in BACKEND_SERVICE_URLS or FRONTEND_SERVICE_URLS:
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
async def login(response: Response, code: str = Query(...)):
    try:
        import pdb; pdb.set_trace();
        # token_url = "http://keycloak:8080/realms/fastapi-gateway/protocol/openid-connect/token"
        token_url = "http://localhost:8080/realms/fastapi-gateway/protocol/openid-connect/token"
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": "fastapi-client",
                    "code": code,
                    "redirect_uri":"http://localhost:8000/login", # should be same as keycloak client valid redirect url
                   "client_secret": "MzMviT0YOxAC2qwIOTVPByYtMNnrzXBo" #Replace with your client secret if required by Keycloak configuration
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            token_response.raise_for_status()
            token_data = token_response.json()

            #Add cookie with token data
            for key, value in token_data.items():
                response.set_cookie(key=key, value=value, httponly=True)

            return RedirectResponse(url="http://localhost:4200/restaurants")

    except httpx.HTTPError as e:
        print(f"Keycloak Authentication failed: {e}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")
    except KeyError as e:
        print(f"Invalid Keycloak response: Missing key {e}")
        raise HTTPException(status_code=500, detail="Invalid Keycloak response")
    except Exception as e:
        print(f"Unexpected error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
