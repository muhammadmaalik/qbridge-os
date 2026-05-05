from qiskit_aer import AerSimulator

class ComputeManager:
    def __init__(self, api_token=None, mode="local"):
        self.api_token = api_token
        self.mode = mode.lower()
        self.backend = None

    def get_backend(self):
        """Intelligently routes the quantum circuit to the right hardware."""
        if self.mode == "local" or not self.api_token:
            print("[Q-Bridge Router] Routing to Local AerSimulator (0 Cost)")
            self.backend = AerSimulator()
            return self.backend
        
        elif self.mode == "cloud":
            print("[Q-Bridge Router] Connecting to IBM Quantum Cloud... (WARNING: Consuming QPU Quota)")
            from qiskit_ibm_runtime import QiskitRuntimeService
            try:
                service = QiskitRuntimeService(channel="ibm_quantum", token=self.api_token)
                self.backend = service.least_busy(operational=True, simulator=False)
                print(f"[Q-Bridge Router] Successfully routed to {self.backend.name}")
                return self.backend
            except Exception as e:
                print(f"[Q-Bridge Router] Cloud auth failed, falling back to local. Error: {e}")
                self.backend = AerSimulator()
                return self.backend
