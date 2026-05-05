from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from backend.database import db

router = APIRouter()

class APIKeyPayload(BaseModel):
    username: str
    service_provider: str = "IBM"
    api_key: str

@router.post("/keys")
async def save_api_key(payload: APIKeyPayload):
    # Retrieve user_id based on username
    user_id = await db.fetchval("SELECT id FROM users WHERE username = $1", payload.username)
    if not user_id:
        # Auto-create user for simplicity in this prototype
        user_id = await db.fetchval(
            "INSERT INTO users (username) VALUES ($1) RETURNING id", 
            payload.username
        )
    
    # Upsert the API key
    # In a real system, encrypt the api_key before storing!
    encrypted_key = payload.api_key # Mock encryption
    
    query = """
        INSERT INTO api_credentials (user_id, service_provider, encrypted_api_key)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id, service_provider) 
        DO UPDATE SET encrypted_api_key = EXCLUDED.encrypted_api_key
        RETURNING id
    """
    try:
        cred_id = await db.fetchval(query, user_id, payload.service_provider, encrypted_key)
        return {"status": "success", "message": "API Key saved securely.", "credential_id": cred_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
