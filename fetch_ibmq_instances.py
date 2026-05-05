import sys
from qiskit_ibm_runtime import QiskitRuntimeService

def main():
    token = "nIFfUAnV8J4BgZwZyEdh6daNMKe_byYwwq-801xtSbpJ"
    try:
        service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
        print("Successfully authenticated.")
        
        instances = service.instances()
        print("Your Authorized Instances:")
        for inst in instances:
            print(f"- {inst}")
            
    except Exception as e:
        print(f"Error fetching instances: {e}")

if __name__ == "__main__":
    main()
