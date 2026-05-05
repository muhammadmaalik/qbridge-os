import os
import json
import time
import sys

# Ensure the parent directory is in the path to load the SDK
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from sdks.python.qbridge_sdk import QBridgeClient

def main():
    print("=" * 60)
    print(" QBridge Secure Enterprise Compiler API")
    print(" Live Benchmark Execution Demo")
    print("=" * 60 + "\n")
    
    # 1. Initialize the Secure E2EE API Client
    client = QBridgeClient("http://localhost:8000")
    
    # 2. Locate Benchmarks
    benchmark_dir = "../Bitcamp-2026-Quantum/Computational Track/starter_kit/"
    
    if not os.path.exists(benchmark_dir):
        raise FileNotFoundError(f"[CRITICAL ERROR] The required benchmark directory '{benchmark_dir}' does not exist! Aborting demo.")
        
    # Dynamically load the starter_kit python modules
    sys.path.append(os.path.abspath(benchmark_dir))
    try:
        from benchmarks import BENCHMARKS
        from hardware import HARDWARE_EDGES
    except ImportError as e:
        raise ValueError(f"[CRITICAL ERROR] Failed to load python modules from '{benchmark_dir}'. Aborting.")
        
    benchmarks = []
    hardware = [list(e) for e in HARDWARE_EDGES]
    
    for name, prog in BENCHMARKS.items():
        benchmarks.append({
            "name": f"{name} (Benchmark)",
            "program": [list(op) for op in prog],
            "hardware": hardware
        })

    # 3. Stream data securely to the remote Compiler Engine
    for idx, b in enumerate(benchmarks, 1):
        name = b["name"]
        print(f"[{idx}/{len(benchmarks)}] Securing and transmitting {name} via AES-GCM to QBridge Compiler...")
        
        # Add slight natural delay for the visual presentation effect
        time.sleep(0.6)
        
        try:
            # The Magic Happens Here!
            res = client.optimize_circuit(b["program"], b["hardware"])
            
            score = res.get("score", "N/A")
            routed = res.get("routed_program", [])
            initial = res.get("initial_placement", {})
            
            print(f"      -> Verification: Payload Decrypted & Verified.")
            print(f"      -> Final Score: {score}")
            print(f"      -> Optimized Depth: {len(routed)} physical instructions.")
        except Exception as err:
            print(f"      -> Transmission/API Error: {err}")
            
        print("-" * 60)
        
    print("\n✓ Demo Complete. Intellectual Property preserved.")
    print("============================================================\n")

if __name__ == "__main__":
    main()
