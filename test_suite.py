from qbridge.robotics import QuantumPathfinder
from qbridge.chemistry import MolecularSimulator
from qbridge.ml import QuantumClassifier

def run_tests():
    print("\n=== Q-BRIDGE: UNIVERSAL QUANTUM TOOLKIT DEMO ===\n")
    
    print("--- Quantum Robotics (Maze Routing) ---")
    pathfinder = QuantumPathfinder()
    print(pathfinder.find_fastest_exit())
    # Assuming it returns an ASCII maze string or we just call and print its output
    res = pathfinder.visualize_maze_path(optimal_state="11")
    if res is not None:
        print(res)
    print()
    
    print("--- Quantum Chemistry (VQE) ---")
    simulator = MolecularSimulator()
    print(simulator.simulate_ground_state())
    simulator.visualize_bond_curve(molecule="H2")
    print("--> [SUCCESS] Chemistry Energy Curve saved to chemistry_viz.png!")
    print()
    
    print("--- Quantum ML (QSVM) ---")
    classifier = QuantumClassifier()
    print(classifier.encode_data_to_quantum([0.8, 0.2]))
    print()

if __name__ == "__main__":
    run_tests()
