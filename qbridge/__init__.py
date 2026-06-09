"""
qbridge - Universal Quantum Library
"""
from .core import generate_key
from .pool import EntropyPool
from .sdk import optimize_portfolio, run_vqe, run_vqe_async

# Aliasing a QBridge helper since test_suite requested `from qbridge import QBridge`
class QBridge:
    @staticmethod
    async def generate_key_from_pool(pool: EntropyPool) -> str:
        return await generate_key(pool)

__all__ = [
    "generate_key",
    "EntropyPool",
    "QBridge",
    "MolecularSimulator",
    "QuantumClassifier",
    "QuantumPathfinder",
    "ComputeManager",
    "run_vqe",
    "run_vqe_async",
    "optimize_portfolio",
]

from .services import QuantumPathfinder
from .services import MolecularSimulator
from .services import QuantumClassifier
from .services import ComputeManager
