from logger import logger
from fastapi import FastAPI, Query, Request, HTTPException, Response
from fastapi.middleware import Middleware
from fastapi.responses import RedirectResponse
import httpx

from starlette.middleware.sessions import SessionMiddleware

from keycloak_middleware import KeycloakRedirectMiddleware, request_path
from fastapi.middleware.cors import CORSMiddleware

from session_manager import session_manager
from config import settings, Settings # Import Settings class


app = FastAPI(
    title="FastAPI API Gateway with Keycloak",
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Add your Angular app's URL here
            allow_credentials=True,  # Important for cookies and authorization
            allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
            allow_headers=["*"],  # Allow all headers
        ),
        Middleware(SessionMiddleware, secret_key="some-random-string", same_site="lax"),
        Middleware(KeycloakRedirectMiddleware), # Remove the parameters here
    ],
)

def get_tenant_from_host(host: str) -> str | None:
    if not host:
        return None
    parts = host.split(".")
    if len(parts) >= 2:
        tenant_name = parts[0]
        if tenant_name in settings.tenant_config:
            return tenant_name
    return None


# --- Middleware ---
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    """Middleware to determine the tenant and set the appropriate settings"""
    host = request.headers.get("host")
    tenant = get_tenant_from_host(host)
    
    # Load tenant settings
    settings = Settings()
    if tenant:
        settings.load_tenant_config(tenant)
    else:
        logger.warning("No tenant found in host, using default settings")
    request.state.settings = settings
    request.state.tenant = tenant
    response = await call_next(request)
    return response


BACKEND_SERVICE_URLS = settings.backend_service_urls

logger.info(f"Backend Service URLs: {BACKEND_SERVICE_URLS}")

FRONTEND_SERVICE_URLS = settings.front_service_urls

logger.info(f"Frontend Service URLs: {FRONTEND_SERVICE_URLS}")

@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway(service: str, path: str, request: Request):
    if service in FRONTEND_SERVICE_URLS:
        ui_url = f"{FRONTEND_SERVICE_URLS[service]}/ui/{path}"
        logger.info(f"Forwarding UI request to: {ui_url}")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=request.method,
                    url=ui_url,
                    headers=request.headers.raw,
                    content=await request.body(),
                    timeout=30 # Added timeout
                )
                response.raise_for_status()  # Raise an exception for bad status codes
                return Response(content=response.content, status_code=response.status_code, headers=response.headers)
            except httpx.HTTPError as e:
                logger.error(f"Error forwarding UI request: {e}")
                return Response(content=e.response.content if e.response else b"Internal Server Error", status_code=e.response.status_code if e.response else 500, headers=e.response.headers if e.response else {})
            except httpx.TimeoutException as e:
                logger.error(f"Timeout error forwarding UI request: {e}")
                return Response(content=b"Request Timeout", status_code=504)
            except Exception as e:
                logger.error(f"Unexpected error forwarding UI request: {e}")
                return Response(content=b"Internal Server Error", status_code=500)

    
    if service not in BACKEND_SERVICE_URLS:
        raise HTTPException(status_code=404, detail="Service not found")
    
    backend_url = f"{BACKEND_SERVICE_URLS[service]}/{path}"

    logger.info(f"Forwarding the request to URL: {backend_url}/{path}")

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
    # Get tenant from host
    host = request.headers.get("host")
    tenant = get_tenant_from_host(host)
    
    # Load tenant settings
    settings = Settings()
    if tenant:
        settings.load_tenant_config(tenant)
    else:
        logger.warning("No tenant found in host, using default settings")
    try:
        # token_url = "http://keycloak:8080/realms/fastapi-gateway/protocol/openid-connect/token"
        token_url = settings.keycloak_token_url
        # import pdb; pdb.set_trace()
        logger.info(f"Token URL is: {token_url}")
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

            logger.info("Bearer and Refresh tokens are generated and added to session successfully")

            original_path = request_path.get('original_path')
            logger.info(f"Original path is: {original_path}")
            if original_path:
                is_valid_path = False
                for service in BACKEND_SERVICE_URLS.keys():
                    if original_path.startswith(f"/{service}"):
                        is_valid_path = True
                        break
                logger.info(f"Is valid path: {is_valid_path}")          
                if is_valid_path:
                    redirect_url = original_path
                else:
                    redirect_url = settings.ui_home_url
            else:
                redirect_url = settings.ui_home_url
            print(f"Redirecting to: {redirect_url}")
            # redirect_url = "http://localhost:8081/ui/restaurants"
            response = RedirectResponse(url=redirect_url)
            return response

    except httpx.HTTPError as e:
        print(f"Keycloak Authentication failed: {e}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")
    except KeyError as e:
        print(f"Invalid Keycloak response: Missing key {e}")
        raise HTTPException(status_code=500, detail="Invalid Keycloak response")
    except Exception as e:
        print(f"Unexpected error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
