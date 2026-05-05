import urllib.request
import json
from typing import Dict, Any, List

class QBridgeClient:
    """
    QBridge High-Level Python SDK
    Bridges Data Scientists and Developers to Quantum hardware without exposing physics logic.
    """
    
    def __init__(self, api_endpoint: str = "https://axesq.us"):
        """Initialize the SDK against the master QBridge node."""
        self.api_endpoint = api_endpoint.rstrip('/')
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'QBridge-Python-SDK/1.0'
        }

    def _post(self, path: str, payload: dict) -> Dict[str, Any]:
        """Internal HTTP POST wrapper"""
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(f"{self.api_endpoint}{path}", data=data, headers=self.headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            raise ConnectionError(f"QBridge Tunnel Failure: {str(e)}")

    def simulate_molecule(self, molecule: str = "H2", bond_distance: float = 0.74, temperature: float = 298.0) -> Dict[str, Any]:
        """
        Executes a remote Variational Quantum Eigensolver (VQE) algorithm.
        Just pass the chemical attributes and QBridge calculates the physical rotation automatically.
        """
        print(f"[QBridge SDK] Routing molecular blueprint ({molecule}) out to physics engine...")
        payload = {"molecule": molecule, "bond_distance": bond_distance, "temperature": temperature}
        response = self._post("/api/services/chemistry", payload)
        if response.get("success"):
            return response.get("data", {})
        raise RuntimeError(f"Molecular Mapping Error: {response.get('error')}")

    def run_robotics(self, grid_size: int = 4, obstacles: List[List[int]] = None) -> Dict[str, Any]:
        """
        Executes a Quantum Pathfinder algorithm mapping interference routing.
        """
        print(f"[QBridge SDK] Plotting {grid_size}x{grid_size} drone grid over Quantum pathfinder...")
        payload = {"grid_size": grid_size, "obstacles": obstacles or []}
        response = self._post("/api/services/robotics", payload)
        if response.get("success"):
            return response.get("data", {})
        raise RuntimeError(f"Pathfinder Error: {response.get('error')}")

    def run_ml(self, tensor_array: List[float] = [0.45, 0.99]) -> Dict[str, Any]:
        """
        Feeds classical arrays into a multi-dimensional ZZFeatureMap for Anomaly Classification.
        """
        print(f"[QBridge SDK] Processing classical tensor array: {tensor_array}...")
        payload = {"tensor_array": tensor_array}
        response = self._post("/api/services/ml", payload)
        if response.get("success"):
            return response.get("data", {})
        raise RuntimeError(f"Machine Learning Engine Error: {response.get('error')}")

    def optimize_circuit(self, program: List[List[Any]], hardware_graph: List[List[int]]) -> Dict[str, Any]:
        """
        Executes a baseline optimal SWAP-routing Compiler placement on a quantum network graph.
        """
        print(f"[QBridge SDK] Optimizing quantum program of size {len(program)}...")
        payload = {"program": program, "hardware_edges": hardware_graph}
        response = self._post("/optimize_circuit", payload)
        if "error" in response:
            raise RuntimeError(f"Optimization Error: {response.get('error')}")
        return response

# ==========================================
# Example Developer Usage:
# ==========================================
if __name__ == "__main__":
    try:
        client = QBridgeClient("https://axesq.us")
        
        # Scenario 1: A pharma researcher modeling an atomic bond stretch
        chem = client.simulate_molecule("H2O", bond_distance=0.96)
        print("\n--- Chemistry Result ---")
        print(f"Energy Level: {chem.get('ground_state_energy')}")
        
        # Scenario 2: A drone developer creating a route around 3 obstacles
        robot = client.run_robotics(grid_size=4, obstacles=[[1,1], [2,2], [3,0]])
        print("\n--- Robotics Pathing Result ---")
        print(f"Optimal Path Code: {robot.get('optimal_path')} (Confidence: {robot.get('confidence')})")
        
    except Exception as err:
        print(err)
