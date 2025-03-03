from fastapi import Depends, HTTPException, Security
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import JWTError, jwt, jwk
from jose.constants import ALGORITHMS
import httpx

# issuer: http://localhost:8080/realms/fastapi-gateway
# http://keycloak:8080/realms/fastapi-gateway/.well-known/openid-configuration
KEYCLOAK_URL = "http://keycloak:8080/realms/fastapi-gateway"
# KEYCLOAK_URL = "http://localhost:8080/realms/fastapi-gateway"

# http://localhost:8080/realms/fastapi-gateway/protocol/openid-connect/certs
JWKS_URL = f"{KEYCLOAK_URL}/protocol/openid-connect/certs"
ALGORITHM = ALGORITHMS.RS256
# CLEINT_ID = "myclient"


oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{KEYCLOAK_URL}/protocol/openid-connect/auth",
    tokenUrl=f"{KEYCLOAK_URL}/protocol/openid-connect/token"
)

async def get_jwks():
    async with httpx.AsyncClient() as client:
        response = await client.get(JWKS_URL)
        return response.json()

async def verify_token(token: str = Security(oauth2_scheme)):
    try:
        header = jwt.get_unverified_header(token)
        jwks = await get_jwks()
        key = next(
            (key for key in jwks["keys"] if key["kid"] == header["kid"]), None
        )
        if not key:
            raise HTTPException(status_code=403, detail="Invalid token")
        public_key = jwk.construct(key, ALGORITHM)
        payload = jwt.decode(token, public_key, algorithms=[ALGORITHM], audience="account")
        return payload
    except JWTError as e:
        if "expired" in str(e):
            # Token expired, try refresh
            return await refresh_token(token)
        else:
            # redirect response with URI
            # Create one more end point - fetch-keycloak-token
            raise HTTPException(status_code=403, detail="Invalid token")
    except Exception as ex:
        raise HTTPException(status_code=403, detail="Could not validate credentials")


async def refresh_token(token: str):
    try:
        token_url = "http://localhost:8080/realms/fastapi-gateway/protocol/openid-connect/token"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": CLIENT_ID,
                    "refresh_token": extract_refresh_token(token), # You need to implement this function
                    "client_secret": CLIENT_SECRET
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data["access_token"]
            return verify_token(access_token) #Verify the new token
    except httpx.HTTPError as e:
        raise HTTPException(status_code=401, detail=f"Token refresh failed: {e}")
    except KeyError as e:
        raise HTTPException(status_code=500, detail="Invalid Keycloak response")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error during refresh: {e}")
