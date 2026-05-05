import requests
import time

API_URL = "https://qbridge-os.onrender.com/api/v1/quantum-key"
DEVICE_ID = "Smart-Meter-01"

def simulate():
    print(f"--- Initializing {DEVICE_ID} IoT Simulator ---")
    # Simulate a smart edge device emitting encrypted packets periodically
    while True:
        try:
            print(f"\n[IoT Device: {DEVICE_ID}] Requesting Quantum Key...")
            response = requests.get(API_URL, params={"device_id": DEVICE_ID})
            response.raise_for_status()
            
            data = response.json()
            key = data.get("quantum_key")
            
            print(f"[SUCCESS] Received 256-bit Key: {key[:8]}...{key[-8:]}")
            print(f"[ENCRYPTING] Payload secured. Transmitting...")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to connect to Q-Bridge Gateway. Retrying...")
            
        time.sleep(2)

if __name__ == "__main__":
    simulate()
