from fastapi import FastAPI, Form, Query, Request, Depends, HTTPException
import httpx
from auth import verify_token

app = FastAPI(title="FastAPI API Gateway with Keycloak")

BACKEND_SERVICE_URLS = {
    "service1": "http://service1:8001",
    "service2": "http://service2:8002",
}

@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway(service: str, path: str, request: Request, user: dict = Depends(verify_token)):
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

# /home - 

# Service-3

# Keycloak service - redirect

# Login page - Submit - API gateway call [/login] with username and password and response with token

# Create an API - for curl command inside API gateway service.

## http://localhost:8080/realms/fastapi-gateway/protocol/openid-connect/auth?client_id=fastapi-client&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Flogin&response_type=code&scope=openid


@app.get("/login")
async def login(code: str = Query(...)):
    # import pdb; pdb.set_trace()
    print(f"code is: {code}")
    try:
        # token_url = "http://keycloak:8080/realms/fastapi-gateway/protocol/openid-connect/token"
        token_url = "http://localhost:8080/realms/fastapi-gateway/protocol/openid-connect/token"
        async with httpx.AsyncClient() as client:
            response = await client.post(
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
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        print(f"Keycloak Authentication failed: {e}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")
    except KeyError as e:
        print(f"Invalid Keycloak response: Missing key {e}")
        raise HTTPException(status_code=500, detail="Invalid Keycloak response")
    except Exception as e:
        print(f"Unexpected error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

@app.post("/login-token")
async def login(username: str = Form(...), password: str = Form(...)):
    try:
        # token_url = "http://keycloak:8080/realms/fastapi-gateway/protocol/openid-connect/token"
        token_url = "http://localhost:8080/realms/fastapi-gateway/protocol/openid-connect/token"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "password",
                    "client_id": "fastapi-client",
                    "username": username,
                    "password": password,
                    "client_secret": "MzMviT0YOxAC2qwIOTVPByYtMNnrzXBo" #Replace with your client secret
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            response.raise_for_status()
            # token_data = response.json()
            # access_token = token_data["access_token"]
            # return {"access_token": access_token}
            return response.json()
    except httpx.HTTPError as e:
        print(f"Keycloak Authentication failed: {e}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")
    except KeyError as e:
        print(f"Invalid Keycloak response: Missing key {e}")
        raise HTTPException(status_code=500, detail="Invalid Keycloak response")
    except Exception as e:
        print(f"Unexpected error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# http://localhost:8080/realms/master/protocol/openid-connect/auth?client_id=security-admin-console&redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fadmin%2Fmaster%2Fconsole%2F&state=06e1bc06-a4ab-4f46-8dd4-d5465c434e7a&response_mode=query&response_type=code&scope=openid&nonce=290b1111-b556-4e67-870e-28c4ab6b1668&code_challenge=pKVwi3x3b-Y6sUjrGKilG3VswLYIlQ--GHG4riDwPgc&code_challenge_method=S256

# http://localhost:8080/realms/fastapi-gateway/protocol/openid-connect/auth?client_id=fastapi-client&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Flogin&response_type=code&scope=openid
