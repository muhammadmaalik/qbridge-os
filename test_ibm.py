import sys
from qiskit_ibm_runtime import QiskitRuntimeService

def main():
    token = "nIFfUAnV8J4BgZwZyEdh6daNMKe_byYwwq-801xtSbpJ"
    try:
        service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
        backends = service.backends()
        print("Available Backends:")
        for b in backends:
            print(f"- {b.name} (Simulator: {b.simulator})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
