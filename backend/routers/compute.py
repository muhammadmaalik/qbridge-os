from __future__ import annotations

import time
import asyncio
import json
from fastapi import APIRouter, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel, Field, model_validator
from backend.quantum_router import QuantumRouter
from backend.database import db
from backend.routers.security import verify_simulation_request

# REMOVED: from backend.main import manager (This caused the circular import)

router = APIRouter()
qr = QuantumRouter()


def molecule_request_canonical(req: "MoleculeRequest") -> str:
    hw = (req.hardware_provider or "ibm").strip().lower()
    mq = int(req.max_qubits)
    scan_s = (req.scan or "").strip()
    scan_part = f"|scan:{scan_s}"
    noise_part = "|noise:1" if req.noise else "|noise:0"
    if req.smiles and str(req.smiles).strip():
        return f"{req.username}|smiles:{str(req.smiles).strip()}|hw:{hw}|q:{mq}{scan_part}{noise_part}"
    st = str(req.structure or "").strip()
    return f"{req.username}|structure:{st}|hw:{hw}|q:{mq}{scan_part}{noise_part}"


class MoleculeRequest(BaseModel):
    username: str
    structure: str | None = None
    smiles: str | None = None
    hardware_provider: str = Field(
        default="ibm",
        description="ibm (prefer real QPU via Runtime), local (simulator), anu (simulator + ANU entropy tag).",
    )
    max_qubits: int = Field(
        default=28,
        description="Cap Jordan–Wigner qubit width (2 × active spatial orbitals) for IBM/local hardware.",
    )
    scan: str | None = Field(
        default=None,
        description="Optional PES scan start:end:step in Å along the first bond (e.g. 0.5:2.0:0.1).",
    )
    noise: bool = Field(
        default=False,
        description="If true, use qiskit-aer NoiseModel from a fake IBM backend for local VQE.",
    )

    @model_validator(mode="after")
    def require_structure_or_smiles(self):
        has_s = self.smiles and str(self.smiles).strip()
        has_t = self.structure and str(self.structure).strip()
        if not has_s and not has_t:
            raise ValueError("Provide either `structure` (formula/name) or `smiles`.")
        return self


class OracleSketchRequest(BaseModel):
    username: str
    payload: dict


async def run_ibm_job(user_id: str, job_id: str, payload: dict, job_type: str):
    # LOCAL IMPORT: Move this here to break the circular dependency loop
    from backend.main import manager

    await manager.broadcast(f"Starting {job_type} job {job_id} on IBM Quantum...")
    try:
        # Fetch API key
        api_key = await db.fetchval(
            "SELECT encrypted_api_key FROM api_credentials WHERE user_id = $1 AND service_provider = 'IBM'",
            user_id,
        )
        if not api_key:
            api_key = "local_fallback"  # Use dummy key to trigger local simulator fallback

        await db.execute("UPDATE job_logs SET status = 'RUNNING' WHERE id = $1", job_id)

        start_time = time.time()

        if job_type == "SIMULATION":
            result = await qr.simulate_molecule(api_key, payload)
        else:
            result = await qr.oracle_sketch(api_key, payload)

        execution_time_ms = int((time.time() - start_time) * 1000)

        await db.execute(
            "UPDATE job_logs SET status = 'COMPLETED', execution_time_ms = $1, hardware_backend_used = 'ibm_brisbane_sim' WHERE id = $2",
            execution_time_ms,
            job_id,
        )

        if job_type == "SIMULATION":
            broadcast_msg = json.dumps(
                {
                    "type": "result",
                    "job_type": job_type,
                    "status": "success",
                    "job_id": job_id,
                    "execution_time_ms": execution_time_ms,
                    "data": result,
                }
            )
            await manager.broadcast(broadcast_msg)
        else:
            await manager.broadcast(
                f"Job {job_id} COMPLETED. Execution time: {execution_time_ms}ms"
            )

    except Exception as e:
        await db.execute("UPDATE job_logs SET status = 'FAILED' WHERE id = $1", job_id)
        err_msg = str(e)
        try:
            await manager.broadcast(
                json.dumps(
                    {
                        "type": "error",
                        "job_type": job_type,
                        "job_id": job_id,
                        "status": "failed",
                        "message": err_msg,
                    }
                )
            )
        except Exception:
            await manager.broadcast(f"Job {job_id} FAILED: {err_msg}")


@router.post("/molecule")
async def compute_molecule(
    req: MoleculeRequest,
    background_tasks: BackgroundTasks,
    x_qbridge_session: str | None = Header(default=None, alias="X-QBridge-Session"),
    x_qbridge_signature: str | None = Header(default=None, alias="X-QBridge-Signature"),
):
    canonical = molecule_request_canonical(req)
    if not verify_simulation_request(x_qbridge_session, x_qbridge_signature, canonical):
        raise HTTPException(
            status_code=401,
            detail="PQC verification failed: invalid or missing session / MAC (quantum-safe signature).",
        )

    user_id = await db.fetchval("SELECT id FROM users WHERE username = $1", req.username)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    job_id = await db.fetchval(
        "INSERT INTO job_logs (user_id, job_type, status) VALUES ($1, 'SIMULATION', 'PENDING') RETURNING id",
        user_id,
    )

    eff_hw = (req.hardware_provider or "ibm").strip().lower()
    warnings: list[str] = []
    endpoint_ibm_warned = False
    if eff_hw == "ibm":
        api_key_row = await db.fetchval(
            "SELECT encrypted_api_key FROM api_credentials WHERE user_id = $1 AND service_provider = 'IBM'",
            user_id,
        )
        if not api_key_row or str(api_key_row).strip() in ("", "local_fallback"):
            eff_hw = "local"
            endpoint_ibm_warned = True

    payload = {
        "structure": req.structure,
        "smiles": req.smiles,
        "max_qubits": req.max_qubits,
        "hardware_provider": eff_hw,
        "_requested_hardware_provider": (req.hardware_provider or "ibm").strip().lower(),
        "_ibm_endpoint_warned": endpoint_ibm_warned,
        "scan": req.scan,
        "noise": bool(req.noise),
    }
    background_tasks.add_task(
        run_ibm_job,
        user_id,
        job_id,
        payload,
        "SIMULATION",
    )
    return {
        "status": "QUEUED",
        "job_id": job_id,
        "warnings": warnings,
        "engaged_local_fallback": endpoint_ibm_warned,
    }


@router.post("/oracle-sketch")
async def compute_oracle_sketch(
    req: OracleSketchRequest,
    background_tasks: BackgroundTasks,
    x_qbridge_session: str | None = Header(default=None, alias="X-QBridge-Session"),
    x_qbridge_signature: str | None = Header(default=None, alias="X-QBridge-Signature"),
):
    ds = req.payload.get("dataset", "")
    canonical = f"{req.username}|ORACLE|{ds}"
    if not verify_simulation_request(x_qbridge_session, x_qbridge_signature, canonical):
        raise HTTPException(
            status_code=401,
            detail="PQC verification failed: invalid or missing session / MAC.",
        )

    user_id = await db.fetchval("SELECT id FROM users WHERE username = $1", req.username)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    job_id = await db.fetchval(
        "INSERT INTO job_logs (user_id, job_type, status) VALUES ($1, 'ML_ORACLE', 'PENDING') RETURNING id",
        user_id,
    )

    background_tasks.add_task(run_ibm_job, user_id, job_id, req.payload, "ML_ORACLE")
    return {"status": "QUEUED", "job_id": job_id}
