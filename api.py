import time
import asyncio
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

import json
import sqlite3
import hashlib
import secrets
import uuid
from typing import List

import io
import base64
import matplotlib
matplotlib.use('Agg') # Essential for headless fastAPI threading without crashing
import matplotlib.pyplot as plt

try:
    from qiskit import QuantumCircuit
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
    from qiskit_aer import AerSimulator
    from qiskit.visualization import plot_histogram
except ImportError:
    pass

from qbridge import EntropyPool, generate_key, ComputeManager, QuantumPathfinder, MolecularSimulator, QuantumClassifier
from pydantic import BaseModel
from typing import List, Optional, Any, Any

class GateModel(BaseModel):
    type: str # H, X, CX
    target: int
    control: Optional[int] = None

class SimulatorRequest(BaseModel):
    num_qubits: int
    gates: List[GateModel]

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        email TEXT PRIMARY KEY,
                        password_hash TEXT,
                        token TEXT
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS offline_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        to_email TEXT,
                        from_email TEXT,
                        payload TEXT
                    )''')
    conn.commit()
    conn.close()

init_db()

class AuthRequest(BaseModel):
    email: str
    password: str

class QuantumRequest(BaseModel):
    token: str = ""
    mode: str = "local"
# Global Entropy Pool
pool = EntropyPool(pool_size=100)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    print(">>> Starting Q-Bridge Entropy Pool...")
    await pool.start()
    # Briefly wait to allow the pool to generate the first batch of quantum entropy
    await asyncio.sleep(1)
    yield
    # Shutdown actions
    print(">>> Shutting down Q-Bridge Entropy Pool...")
    await pool.stop()

app = FastAPI(title="Q-Bridge IoT Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IBM_KEY = "YOUR_IBM_TOKEN_HERE"

@app.get("/", response_class=HTMLResponse)
async def serve_hub():
    with open("dashboard.html", "r", encoding="utf-8") as file:
        return file.read()

@app.get("/chat", response_class=HTMLResponse)
async def serve_portal():
    with open("axesq_portal.html", "r", encoding="utf-8") as file:
        return file.read()

class ChemistryRequest(BaseModel):
    molecule: str = "H2"
    bond_distance: float = 0.74
    temperature: float = 298.0

class RoboticsRequest(BaseModel):
    grid_size: int = 4
    obstacles: List[List[int]] = []

class MLRequest(BaseModel):
    tensor_array: List[float] = [0.45, 0.99]

@app.post("/api/services/chemistry")
async def run_chemistry(req: ChemistryRequest):
    try:
        sim = MolecularSimulator()
        return {"success": True, "data": sim.simulate_ground_state(req.molecule, req.bond_distance, req.temperature)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/services/robotics")
async def run_robotics(req: RoboticsRequest):
    try:
        pathfinder = QuantumPathfinder()
        ans = pathfinder.find_fastest_exit(grid_size=req.grid_size, obstacles=req.obstacles)
        return {"success": True, "data": ans}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/services/ml")
async def run_ml(req: MLRequest):
    try:
        classifier = QuantumClassifier()
        return {"success": True, "data": classifier.encode_data_to_quantum(req.tensor_array)}
    except Exception as e:
        return {"success": False, "error": str(e)}

import networkx as nx

class OptimizeRequest(BaseModel):
    program: List[List[Any]]
    hardware_edges: List[List[int]]

def used_logical_qubits(program: List[tuple]) -> list[int]:
    logical_qubits = sorted({qubit for op in program for qubit in op[1:]})
    return logical_qubits

def identity_placement(program: list[tuple], hardware_graph: nx.Graph) -> dict[int, int]:
    logical_qubits = used_logical_qubits(program)
    physical_qubits = sorted(hardware_graph.nodes)
    return {logical: physical_qubits[index] for index, logical in enumerate(logical_qubits)}

def solve_baseline(program: list[tuple], hardware_graph: nx.Graph) -> tuple[dict[int, int], list[tuple]]:
    placement = identity_placement(program, hardware_graph)
    routed_program: list[tuple] = []
    physical_to_logical = {physical: logical for logical, physical in placement.items()}

    for op in program:
        kind = op[0]
        if kind == "1Q":
            logical = op[1]
            routed_program.append(("1Q", placement[logical]))
            continue

        _, logical_left, logical_right = op
        physical_left = placement[logical_left]
        physical_right = placement[logical_right]

        if not hardware_graph.has_edge(physical_left, physical_right):
            path = nx.shortest_path(hardware_graph, physical_left, physical_right)
            for left, right in zip(path[:-2], path[1:-1]):
                left_logical = physical_to_logical.get(left)
                right_logical = physical_to_logical.get(right)
                routed_program.append(("SWAP", left, right))
                physical_to_logical[left], physical_to_logical[right] = right_logical, left_logical
                if left_logical is not None:
                    placement[left_logical] = right
                if right_logical is not None:
                    placement[right_logical] = left

        routed_program.append(("2Q", placement[logical_left], placement[logical_right]))

    return identity_placement(program, hardware_graph), routed_program

def schedule_layers_ordered(routed_program: list[tuple]) -> list[list[tuple]]:
    layers: list[list[tuple]] = []
    qubit_last_layer: dict[int, int] = {}
    for op in routed_program:
        if op[0] == "1Q":
            continue
        wires = op[1:]
        layer_index = 1 + max((qubit_last_layer.get(qubit, 0) for qubit in wires), default=0)
        while len(layers) < layer_index:
            layers.append([])
        layers[layer_index - 1].append(op)
        for qubit in wires:
            qubit_last_layer[qubit] = layer_index
    return layers

def core_score(routed_program: list[tuple]) -> float:
    swap_count = sum(1 for op in routed_program if op[0] == "SWAP")
    depth = len(schedule_layers_ordered(routed_program))
    return float(swap_count + 0.5 * depth)

@app.post("/optimize_circuit")
async def optimize_circuit_api(req: OptimizeRequest):
    try:
        program = [tuple(op) for op in req.program]
        graph = nx.Graph()
        graph.add_edges_from([tuple(e) for e in req.hardware_edges])
        placement, routed_program = solve_baseline(program, graph)
        score = core_score(routed_program)
        return {
            "initial_placement": placement,
            "routed_program": routed_program,
            "score": score
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/educator", response_class=HTMLResponse)
async def serve_educator():
    with open("axesq_educator.html", "r", encoding="utf-8") as file:
        return file.read()

@app.post("/api/educator/simulate")
async def simulate_circuit(req: SimulatorRequest):
    try:
        qc = QuantumCircuit(req.num_qubits)
        for gate in req.gates:
            g_type = gate.type.upper()
            if g_type == 'H':
                qc.h(gate.target)
            elif g_type == 'X':
                qc.x(gate.target)
            elif g_type == 'Y':
                qc.y(gate.target)
            elif g_type == 'Z':
                qc.z(gate.target)
            elif g_type == 'CX':
                qc.cx(gate.control, gate.target)
            elif g_type == 'SWAP':
                qc.swap(gate.control, gate.target)
                
        # 1. Render Circuit as Image
        fig_circuit = qc.draw(output='mpl')
        buf_circ = io.BytesIO()
        fig_circuit.savefig(buf_circ, format='png', bbox_inches='tight', facecolor='#050505')
        plt.close(fig_circuit)
        b64_circ = base64.b64encode(buf_circ.getvalue()).decode('utf-8')
        
        # 2. Simulate
        qc.measure_all()
        sim = AerSimulator()
        job = sim.run(qc, shots=1024)
        counts = job.result().get_counts()
        
        # 3. Render Histogram
        fig_hist = plot_histogram(counts, color='#00ff88')
        fig_hist.patch.set_facecolor('#050505')
        ax = fig_hist.gca()
        ax.set_facecolor('#050505')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        
        buf_hist = io.BytesIO()
        fig_hist.savefig(buf_hist, format='png', bbox_inches='tight', facecolor='#050505')
        plt.close(fig_hist)
        b64_hist = base64.b64encode(buf_hist.getvalue()).decode('utf-8')
        
        return {
            "success": True,
            "raw_counts": counts,
            "circuit_image": f"data:image/png;base64,{b64_circ}",
            "histogram_image": f"data:image/png;base64,{b64_hist}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

pending_keys = {}

def fetch_anu_quantum_entropy():
    print(">>> Fetching True Quantum Entropy from ANU...")
    try:
        import urllib.request
        import json
        req = urllib.request.Request("https://qrng.anu.edu.au/API/jsonI.php?length=32&type=uint8", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            anu_data = json.loads(response.read().decode())
            # Array of 32 physical quantum uint8 values (256-bits total)
            quantum_bytes = bytes(anu_data["data"])
            anu_hex = quantum_bytes.hex()
            return anu_hex, "ANU_Quantum_Vacuum", "ANU Labs Generator"
    except Exception as anu_e:
        print(f"ANU QRNG Error: {str(anu_e)}")
        import secrets
        return secrets.token_hex(32), "System_Random_Fallback", "Local Entropy Pool"

@app.get("/generate_key")
async def generate_key_api(token: str = ""):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE token=?", (token,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"error": "Unauthorized"}

    key, source, hw = await asyncio.to_thread(fetch_anu_quantum_entropy)
    key_id = str(uuid.uuid4())
    
    pending_keys[key_id] = {
        "key": key,
        "source": source,
        "hw": hw
    }
    
    print(f"[!] Ephemeral Key Generated: {key_id}")
    return {"key": key, "key_id": key_id, "source": source, "hardware": hw}

@app.get("/consume_key")
async def consume_key_api(token: str = "", key_id: str = ""):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE token=?", (token,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"error": "Unauthorized"}

    if key_id not in pending_keys:
        return {"error": "Key not found or already consumed"}

    # Quantum Key Collapse - Instantly delete from memory!
    data = pending_keys.pop(key_id)
    print(f"[!] Ephemeral Key Collapsed/Consumed: {key_id}")
    
    return {
        "key": data["key"],
        "source": data["source"],
        "hardware": data["hw"]
    }



@app.post("/api/register")
async def register(req: AuthRequest):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    password_hash = hashlib.sha256(req.password.encode()).hexdigest()
    token = secrets.token_hex(16)
    try:
        cursor.execute("INSERT INTO users (email, password_hash, token) VALUES (?, ?, ?)", (req.email, password_hash, token))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
        token = ""
    conn.close()
    if success:
        return {"success": True, "token": token, "email": req.email}
    else:
        return {"success": False, "error": "Email already registered"}

@app.post("/api/login")
async def login(req: AuthRequest):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    password_hash = hashlib.sha256(req.password.encode()).hexdigest()
    cursor.execute("SELECT token FROM users WHERE email=? AND password_hash=?", (req.email, password_hash))
    row = cursor.fetchone()
    
    if row:
        token = secrets.token_hex(16)
        cursor.execute("UPDATE users SET token=? WHERE email=?", (token, req.email))
        conn.commit()
        conn.close()
        return {"success": True, "token": token, "email": req.email}
    else:
        conn.close()
        return {"success": False, "error": "Invalid credentials"}

class ConnectionManager:
    def __init__(self):
        # Map email to active WebSocket
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, email: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[email] = websocket

    def disconnect(self, email: str):
        if email in self.active_connections:
            del self.active_connections[email]

    async def send_personal_message(self, message: str, email: str):
        if email in self.active_connections:
            await self.active_connections[email].send_text(message)

ws_manager = ConnectionManager()

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket, token: str = ""):
    if not token:
        await websocket.close(code=1008)
        return

    # Verify session token against DB
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE token=?", (token,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        await websocket.close(code=1008)
        return

    email = row[0]
    await ws_manager.connect(email, websocket)
    
    # Notify user they connected
    await websocket.send_text(json.dumps({"system": f"Connected as {email}"}))

    # Flush offline messages immediately
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, payload FROM offline_messages WHERE to_email=?", (email,))
    rows = cursor.fetchall()
    for stored_msg in rows:
        msg_id, msg_payload = stored_msg
        await websocket.send_text(msg_payload)
        cursor.execute("DELETE FROM offline_messages WHERE id=?", (msg_id,))
    conn.commit()
    conn.close()

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                target_email = payload.get("to")
                
                # Stamp the envelope with authenticated sender identity
                payload["from"] = email
                
                if target_email:
                    if target_email in ws_manager.active_connections:
                        # Point-to-Point delivery
                        await ws_manager.send_personal_message(json.dumps(payload), target_email)
                    else:
                        # Offline storage
                        db_conn = sqlite3.connect("users.db")
                        db_cursor = db_conn.cursor()
                        db_cursor.execute("INSERT INTO offline_messages (to_email, from_email, payload) VALUES (?, ?, ?)", (target_email, email, json.dumps(payload)))
                        db_conn.commit()
                        db_conn.close()
            except json.JSONDecodeError:
                pass # Ignore malformed drops
    except WebSocketDisconnect:
        ws_manager.disconnect(email)
