from fastapi import Depends, HTTPException, Security
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import JWTError, jwt, jwk
from jose.constants import ALGORITHMS
import httpx

from logger import logger

from session_manager import session_manager
from config import settings, Settings # Import Settings class

# KEYCLOAK_URL = "http://keycloak:8080/realms/fastapi-gateway"
# KEYCLOAK_URL = settings.keycloak_url # Remove this line



JWKS_URL = "" # Remove this line
ALGORITHM = ALGORITHMS.RS256
# CLEINT_ID = "myclient"


oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="", # Remove this line
    tokenUrl="" # Remove this line
)

async def get_jwks(settings: Settings): # Add settings parameter
    # import pdb; pdb.set_trace()
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.keycloak_url}/protocol/openid-connect/certs") # Use settings here
        return response.json()

async def verify_token(token: str, settings: Settings): # Add settings parameter
    logger.info(f"Verifying the token with Keycloak service: {token}")
    try:
        header = jwt.get_unverified_header(token)
        logger.info(f"header is: {header}")
        jwks = await get_jwks(settings) # Pass settings here
        key = next(
            (key for key in jwks["keys"] if key["kid"] == header["kid"]), None
        )
        if not key:
            logger.info("Key not found, Invalid token")
            raise HTTPException(status_code=403, detail="Invalid token")
        public_key = jwk.construct(key, ALGORITHM)
        payload = jwt.decode(token, public_key, algorithms=[ALGORITHM], audience="account")
        logger.info("Token Verified successfully, forwarding the request")
        return payload
    except JWTError as e:
        logger.error(f"JWT Error: {e}")
        if "expired" in str(e):
            # Token expired, try refresh
            session_data = session_manager.get_session(token)
            if session_data:
                logger.info("Token expired, trying to refresh")
                return await refresh_token(session_data["refresh_token"], settings) # Pass settings here
            else:
                raise HTTPException(status_code=403, detail="Invalid token")
        else:
            raise HTTPException(status_code=403, detail="Invalid token")
    except Exception as ex:
        logger.error(f"Error verifying token: {ex}")
        raise HTTPException(status_code=403, detail="Could not validate credentials")


async def refresh_token(refresh_token: str, settings: Settings): # Add settings parameter
    try:
        logger.info("Trying to refresh the token")
        token_url = settings.keycloak_token_url
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.client_id,
                    "refresh_token": refresh_token, # You need to implement this function
                    "client_secret": settings.client_secret,
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data["access_token"]
            return verify_token(access_token, settings) #Verify the new token, pass settings
    except httpx.HTTPError as e:
        raise HTTPException(status_code=401, detail=f"Token refresh failed: {e}")
    except KeyError as e:
        raise HTTPException(status_code=500, detail="Invalid Keycloak response")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error during refresh: {e}")
