import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.quantum_router import QuantumRouter
from backend.database import db

router = APIRouter()
qr = QuantumRouter()

class EntropyRequest(BaseModel):
    username: str

@router.post("")
@router.get("")
async def get_entropy(username: str = "testuser"):
    start_time = time.time()
    
    user_id = await db.fetchval("SELECT id FROM users WHERE username = $1", username)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Log the job as PENDING
    job_id = await db.fetchval(
        "INSERT INTO job_logs (user_id, job_type, status) VALUES ($1, 'ENTROPY', 'PENDING') RETURNING id",
        user_id
    )
    
    try:
        # Fetch entropy via Path A
        entropy_data = await qr.fetch_anu_entropy()
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Update job to COMPLETED
        await db.execute(
            "UPDATE job_logs SET status = 'COMPLETED', execution_time_ms = $1, hardware_backend_used = 'ANU_VACUUM' WHERE id = $2",
            execution_time_ms, job_id
        )
        
        return {
            "job_id": job_id,
            "status": "COMPLETED",
            "entropy": entropy_data,
            "execution_time_ms": execution_time_ms
        }
    except Exception as e:
        # Update job to FAILED
        await db.execute("UPDATE job_logs SET status = 'FAILED' WHERE id = $1", job_id)
        raise HTTPException(status_code=500, detail=str(e))
