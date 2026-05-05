from sdks.python.qbridge_sdk import QBridgeClient

def main():
    client = QBridgeClient("https://qbridge-os.onrender.com")
    
    # Tiny linear program: H on 0, CX on 0-1, CX on 1-2
    program = [
        ["1Q", 0],
        ["2Q", 0, 1],
        ["2Q", 1, 2]
    ]
    # Linear hardware graph: 0-1-2
    hardware = [
        [0, 1],
        [1, 2]
    ]
    
    print("Testing Optimizer...")
    res = client.optimize_circuit(program, hardware)
    print("Success! Score:", res.get("score"))
    print("Initial Placement:", res.get("initial_placement"))
    print("Routed:", res.get("routed_program"))

if __name__ == "__main__":
    main()
