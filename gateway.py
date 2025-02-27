from fastapi import FastAPI, Request, Depends, HTTPException
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
