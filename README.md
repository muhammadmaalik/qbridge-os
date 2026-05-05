# QBridge: Secure Quantum Infrastructure Gateway

## Overview
**QBridge** is an enterprise-grade, abstracted Python SDK and API Gateway designed to bridge the massive gap between classical developers and complex quantum mechanics. It allows developers, data scientists, and engineers to interact with cutting-edge quantum algorithms seamlessly without ever handwriting a single low-level physics instruction (`Qiskit`).

Crucially, **QBridge is a Secure API Tunnel**. Because quantum circuit blueprints (IP) are highly valuable, QBridge utilizes **True Quantum Randomness** (derived from Australian National University vacuum fluctuations) to generate cryptographically secure AES-GCM keys. This ensures unoptimized proprietary data is transmitted securely from client edge environments directly to the routing server.

---

## 🏗️ The QBridge Library Capabilities (The 4 Pillars)

The QBridge library is divided into four distinct computational pillars. All you have to do is pass the standard data structures you are used to, and the backend engine securely manages the rest.

### 1. Quantum Chemistry (Variational Quantum Eigensolver)
**Use Case:** Accelerating molecular simulation.
Instead of building a Hamiltonian matrix manually, simply pass a molecule and its dimensions. QBridge natively calculates identical ground-state physical rotations automatically.
```python
chem_result = client.simulate_molecule(molecule="H2O", bond_distance=0.96)
```

### 2. Quantum Robotics (Interference Pathfinding)
**Use Case:** Navigating dynamic drone flight paths or routing around physical obstacles.
Pass a standard 2D dimensional array mapping your grid and obstacle coordinates. The SDK feeds this to a quantum interference algorithm that massively accelerates state-space BFS evaluations.
```python
robot_result = client.run_robotics(grid_size=4, obstacles=[[1,1], [2,2]])
```

### 3. Machine Learning (ZZFeatureMap Hilbert Encoding)
**Use Case:** Anomaly detection and classification models.
Load native classical float arrays straight into the SDK. The system effortlessly maps your tensors into a higher-dimensional quantum state vector, paving the way for Quantum Support Vector Machine learning.
```python
ml_result = client.run_ml(tensor_array=[0.45, 0.99, -0.21])
```

### 4. Hardware Optimization & SWAP Routing (Hackathon Computational Track)
**Use Case:** Processing unmapped logic to physical hardware.
If you know your logical inputs but have restrictive hardware edge matrices, our advanced compiler natively digests it. It dictates rapid heuristic placement, inserts required SWAP logic, and returns a verified runtime score mapping.
```python
# Pass naive programs to constrained hardware matrices
res = client.optimize_circuit(program=logical_program, hardware_graph=hardware_topology)
```

---

## 🚀 Startup Instructions

To fully run the QBridge infrastructure locally or on a production server:

### 1. Install Dependencies
Ensure you have the core packages installed.
```bash
pip install fastapi uvicorn qiskit networkx websockets
```

### 2. Boot the QBridge FastAPI Server
First, spin up the central compiler backend. This engine receives secure instructions and processes the physical qubits in the background. Note: this keeps your "Entropy Pool" actively caching AES keys.
```bash
# From the qbridge_project directory
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

### 3. Exposing the API (Optional but Recommended)
To accept remote queries (e.g., from an edge drone device or a remote Jupyter Notebook), pipe your local API outward using Cloudflare.
```bash
cloudflared tunnel --url http://127.0.0.1:8000 run your-tunnel-name
```
*Your frontend endpoint will now route to your locally hosted QBridge Server (e.g., `https://axesq.us`)*

### 4. Run the Full Capabilities Demo
We have bundled a comprehensive demonstration showcasing how seamlessly a developer utilizes the `QBridgeClient` across all four application domains natively in Python. Make sure your server (step 2) is running first!
```bash
python library_demo.py
```
