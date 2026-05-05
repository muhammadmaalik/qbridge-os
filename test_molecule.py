import asyncio
from backend.quantum_router import QuantumRouter

async def test():
    router = QuantumRouter()
    try:
        # Pass a dummy API key since it might fail and fallback to local simulator
        res = await router.simulate_molecule("dummy_key", {"structure": "H2"})
        print("Success:", res)
    except Exception as e:
        print("Error during simulate_molecule:", type(e), e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
