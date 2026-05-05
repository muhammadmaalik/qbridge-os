import asyncio
import time
from qbridge import EntropyPool, generate_key

async def main():
    print("=== Q-Bridge Library Test ===")
    
    print("\n[1] Starting async Entropy Pool with Qiskit Simulator...")
    pool = EntropyPool(pool_size=100)
    await pool.start()
    
    print("Waiting slightly for pool to populate (calculating quantum superposition)...")
    await asyncio.sleep(1.0) # Wait a bit longer since qiskit simulation takes a moment
    
    # Test asynchronous Entropy Pool key derivation
    print("\n[2] Testing async Entropy Pool for zero-latency 256-bit keys...")
    for i in range(3):
        start_t = time.time()
        key = await generate_key(pool)
        elapsed = (time.time() - start_t)*1000
        print(f"Instantly fetched 256-bit key {i+1}: {key} (in {elapsed:.2f} ms)")
        
    await pool.stop()
    print("\nTest completed successfully! The Quantum simulated keys are ready.")

if __name__ == "__main__":
    asyncio.run(main())
