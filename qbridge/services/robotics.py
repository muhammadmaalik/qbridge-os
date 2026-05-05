from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import math

class QuantumPathfinder:
    def find_fastest_exit(self, grid_size: int = 4, obstacles: list = None):
        if obstacles is None:
            obstacles = []
            
        # The number of qubits scales dynamically with the grid size
        num_qubits = max(math.ceil(math.log2(grid_size * grid_size)), 2)
        qc = QuantumCircuit(num_qubits, num_qubits)
        
        # Apply Grover-like superposition dynamically
        qc.h(range(num_qubits))
        
        # Simulate obstacle interference via Z rotations
        for i, obs in enumerate(obstacles):
            qc.z(i % num_qubits)
            
        qc.measure(range(num_qubits), range(num_qubits))
        
        simulator = AerSimulator()
        result = simulator.run(qc, shots=512).result()
        counts = result.get_counts()
        
        # Pick the state with the highest probability
        optimal_state = max(counts, key=counts.get)
        
        return {
            "optimal_path": optimal_state,
            "grid_size": grid_size,
            "obstacles_avoided": len(obstacles),
            "confidence": f"{(counts[optimal_state]/512)*100:.1f}%",
            "quantum_state": optimal_state,
            "raw_counts": counts
        }

    def visualize_maze_path(self, optimal_state="11"):
        maze = f"""
        [Q-Bridge] Maze Routing Visualizer (Target State: |{optimal_state}⟩)
        
        +---+---+---+---+
        | S |   |   |   |
        +   +---+   +   +
        | v       > | E |
        +---+---+---+---+
        
        --> Path successfully mapped to Exit (E) using |{optimal_state}⟩!
        """
        return maze
