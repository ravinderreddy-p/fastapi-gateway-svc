from fastapi import Depends, HTTPException, Security
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import jwt, jwk
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
    jwks = await get_jwks()
    try:
        header = jwt.get_unverified_header(token)
        key = next(
            (key for key in jwks["keys"] if key["kid"] == header["kid"]), None
        )
        if not key:
            raise HTTPException(status_code=403, detail="Invalid token")
        public_key = jwk.construct(key, ALGORITHM)
        payload = jwt.decode(token, public_key, algorithms=[ALGORITHM], audience="account")
        return payload
    except Exception as ex:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
