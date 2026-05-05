import asyncio
import logging
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

logger = logging.getLogger(__name__)

class EntropyPool:
    """
    Asynchronous background Entropy Pool.
    Maintains a pool of pre-generated raw 16-bit quantum strings.
    """
    
    def __init__(self, pool_size: int = 100):
        self.pool_size = pool_size
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=pool_size)
        self._worker_task = None
        self._running = False
        self.sim = AerSimulator()

    def _generate_quantum_batch(self):
        qc = QuantumCircuit(16, 16)
        qc.h(range(16))
        qc.measure(range(16), range(16))
        compiled_circuit = transpile(qc, self.sim)
        job = self.sim.run(compiled_circuit, shots=16)
        counts = job.result().get_counts()
        
        results = []
        for state, count in counts.items():
            for _ in range(count):
                results.append(state)
        return results

    async def start(self):
        """Start the background worker to populate the entropy pool."""
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())

    async def stop(self):
        """Stop the background worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def _worker(self):
        """Background task loop that constantly fills the pool with new quantum strings."""
        while self._running:
            try:
                batch = self._generate_quantum_batch()
                for b_string in batch:
                    await self._pool.put(b_string)
                    logger.debug("New raw quantum string added to pool.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error generating batch in worker: {e}")
                await asyncio.sleep(1)

    async def get_raw_string(self) -> str:
        """
        Request a 16-bit raw quantum string.
        Returns instantly if the pool is populated.
        """
        return await self._pool.get()
