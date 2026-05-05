import time
import sys
import os

# Ensure the parent directory is in the python path to load the SDK module correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from sdks.python.qbridge_sdk import QBridgeClient

def main():
    print("============================================================")
    print(" QBridge Secure Enterprise SDK - Comprehensive Feature Demo ")
    print("============================================================\n")
    
    # =========================================================
    # Phase 0: INITIALIZATION
    # =========================================================
    # We initialize the QBridgeClient instance. This abstracted class
    # securely maps all our requests to the FastAPI backend over HTTP
    # utilizing End-to-End Encryption backed by ANU Quantum Randomness.
    # ---------------------------------------------------------
    try:
        # Using localhost. If running against production, this would be "https://axesq.us"
        client = QBridgeClient("https://qbridge-os.onrender.com")
        print("[*] Secure API Client Initialized successfully.")
    except Exception as e:
        print(f"[!] Failed to initialize client: {e}")
        return
        
    time.sleep(1)

    # =========================================================
    # Application 1: Quantum Chemistry (Molecular Simulation)
    # =========================================================
    print("\n" + "-"*60)
    print(" 1. Chemistry Pillar: Variational Quantum Eigensolver (VQE)")
    print("-" * 60)
    print("Scenario: A researcher modeling the ground state energy of a Water (H2O) molecule stretching.")
    
    # VQE maps chemical parameters to physical quantum rotations.
    # The developer NEVER touches a Qiskit circuit. They simply pass the 'H2O' blueprint.
    try:
        chem_result = client.simulate_molecule(molecule="H2O", bond_distance=0.96, temperature=298.0)
        print(" -> Data successfully returned from physics engine.")
        print(f" -> Computed Ground State Energy: {chem_result.get('ground_state_energy')} Hartrees")
    except Exception as e:
        print(f" -> Execution Failed: {e}")
        
    time.sleep(1)

    # =========================================================
    # Application 2: Quantum Robotics (Pathfinding & Routing)
    # =========================================================
    print("\n" + "-"*60)
    print(" 2. Robotics Pillar: Quantum Pathfinder")
    print("-" * 60)
    print("Scenario: A drone navigating a tightly restricted 4x4 grid filled with physical obstacles.")
    
    # QBridge translates the classical grid coordinate arrays into interference logic
    # finding the optimal path significantly faster than classical BFS/A* searches.
    try:
        robot_result = client.run_robotics(grid_size=4, obstacles=[[1,1], [2,2], [3,0]])
        print(" -> Path calculation retrieved.")
        print(f" -> Optimal Flight Path: {robot_result.get('optimal_path')}")
        print(f" -> Quantum Confidence Metric: {robot_result.get('confidence')}")
    except Exception as e:
        print(f" -> Execution Failed: {e}")
        
    time.sleep(1)

    # =========================================================
    # Application 3: Quantum Machine Learning (Anomaly Detection)
    # =========================================================
    print("\n" + "-"*60)
    print(" 3. Machine Learning Pillar: Multi-Dimensional ZZFeatureMap")
    print("-" * 60)
    print("Scenario: Encoding classic data tensors into higher-dimensional Hilbert spaces for classification analysis.")
    
    # We feed native classical float arrays into the system. QBridge natively converts them
    # into quantum state vectors capable of feeding directly into a Quantum Support Vector Machine.
    try:
        ml_result = client.run_ml(tensor_array=[0.45, 0.99, -0.21, 0.88])
        print(" -> Tensors successfully quantum-encoded.")
        print(f" -> Vector Payload Output: {ml_result}")
    except Exception as e:
        print(f" -> Execution Failed: {e}")
        
    time.sleep(1)

    # =========================================================
    # Application 4: Compiler & Hardware Optimization 
    # =========================================================
    print("\n" + "-"*60)
    print(" 4. Compiler Pillar: Hardware Graph Topology and SWAP Routing")
    print("-" * 60)
    print("Scenario: Compiling an unoptimized logical 3-qubit program onto a physical topology.")
    
    # We pass the naive logical program and the restrictive physical hardware topology graph.
    # QBridge places the logic to minimize SWAPs, and then automatically returns the compiled score
    # representing algorithmic depth + swap penalties perfectly matching the physical boundaries.
    logical_program = [
        ["1Q", 0], 
        ["2Q", 0, 1], 
        ["2Q", 1, 2]
    ]
    hardware_topology = [
        [0, 1], 
        [1, 2]
    ]
    
    try:
        compiler_result = client.optimize_circuit(program=logical_program, hardware_graph=hardware_topology)
        print(" -> Circuit completely compiled.")
        print(f" -> Execution Score (Lower is better): {compiler_result.get('score')}")
        print(f" -> Initial Baseline Qubit Mapping: {compiler_result.get('initial_placement')}")
        print(f" -> Total Output Route Length: {len(compiler_result.get('routed_program'))} Physical Instructions")
    except Exception as e:
        print(f" -> Execution Failed: {e}")

    print("\n============================================================")
    print(" [SUCCESS] SDK Feature Walkthrough Complete.")
    print("============================================================\n")

if __name__ == "__main__":
    main()
