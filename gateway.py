from fastapi import FastAPI, Form, Request, Depends, HTTPException
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


# Service-3

# Keycloak service - redirect

# Login page - Submit - API gateway call [/login] with username and password and response with token

# Create an API - for curl command inside API gateway service.

@app.post("/login")
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
                    "password": password
                    #"client_secret": "your-client-secret" #Replace with your client secret
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
