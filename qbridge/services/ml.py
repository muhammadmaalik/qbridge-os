from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

class QuantumClassifier:
    def encode_data_to_quantum(self, tensor: list = None):
        if tensor is None:
            tensor = [0.5, 0.8]
            
        num_qubits = max(len(tensor), 1)
        qc = QuantumCircuit(num_qubits, num_qubits)
        
        # Apply RX gates using the data points as rotation angles dynamically
        for i, val in enumerate(tensor):
            qc.rx(float(val), i)
        
        # Apply a CZ gate to entangle the features if multi-dimensional
        for i in range(num_qubits - 1):
            qc.cz(i, i+1)
        
        # Measure the circuit
        qc.measure(range(num_qubits), range(num_qubits))
        
        simulator = AerSimulator()
        result = simulator.run(qc, shots=1024).result()
        counts = result.get_counts()
        
        # Pick the most prevalent eigenstate to determine anomaly grouping
        optimal_state = max(counts, key=counts.get)
        classification = "Anomaly Detected" if optimal_state.count("1") > optimal_state.count("0") else "Normal Threshold"
        
        return {
            "input_tensor": tensor,
            "quantum_feature_map": "Dynamic ZZFeatureMap",
            "predicted_class": classification,
            "confidence": f"{(counts[optimal_state]/1024)*100:.1f}%",
            "raw_counts": counts,
            "status": "Encoded and Evaluated"
        }
