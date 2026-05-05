"""
Quantum portfolio optimization using Qiskit Finance :class:`PortfolioOptimization`,
:class:`~qiskit_optimization.converters.QuadraticProgramToQubo`, QAOA, and
:class:`~qiskit_optimization.algorithms.MinimumEigenOptimizer`.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_finance.applications.optimization import PortfolioOptimization
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit_optimization.converters import QuadraticProgramToQubo
from qiskit.primitives import StatevectorSampler


def _budget_half_assets(num_assets: int) -> int:
    """Pick roughly half the universe (ceil(n/2)), at least one asset."""
    return max(1, (num_assets + 1) // 2)


def _to_mu_sigma(
    tickers: list[str],
    expected_returns: dict[str, float] | list[float] | np.ndarray,
    covariance_matrix: list[list[float]] | np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    if isinstance(expected_returns, dict):
        mu = np.array([float(expected_returns[t]) for t in tickers], dtype=np.float64)
    else:
        mu = np.asarray(expected_returns, dtype=np.float64).ravel()
    sigma = np.asarray(covariance_matrix, dtype=np.float64)
    if mu.shape[0] != len(tickers):
        raise ValueError("expected_returns length must match tickers.")
    if sigma.shape != (len(tickers), len(tickers)):
        raise ValueError("covariance_matrix must be square with side len(tickers).")
    # Mild ridge if nearly singular (yahoo covariances can be noisy)
    sigma = 0.5 * (sigma + sigma.T)
    eig_min = np.linalg.eigvalsh(sigma).min()
    if eig_min < 1e-10:
        sigma = sigma + (1e-8 - float(eig_min)) * np.eye(len(tickers))
    return mu, sigma


def optimize_portfolio(
    tickers: list[str],
    expected_returns: dict[str, float] | list[float] | np.ndarray,
    covariance_matrix: list[list[float]] | np.ndarray,
    risk_factor: float = 0.5,
    *,
    budget: int | None = None,
    qaoa_reps: int = 1,
    cobyla_maxiter: int = 150,
) -> dict[str, Any]:
    """
    Build a portfolio QP via :class:`PortfolioOptimization`, convert to QUBO,
    and minimize with QAOA + :class:`MinimumEigenOptimizer` using a
    :class:`~qiskit.primitives.StatevectorSampler` (exact simulation).

    Parameters
    ----------
    tickers
        Ordered symbols (same order as rows/cols of ``covariance_matrix``).
    expected_returns
        Annualized expected returns per ticker (dict keyed by symbol or array).
    covariance_matrix
        Annualized covariance (e.g. from :func:`backend.finance_data.get_stock_data`).
    risk_factor
        Trade-off weight between return and risk in ``PortfolioOptimization``.
    budget
        Number of assets to hold; default ``ceil(n/2)``.
    """
    tickers = [str(t).strip().upper() for t in tickers if str(t).strip()]
    if len(tickers) < 2:
        raise ValueError("Need at least two tickers for portfolio optimization.")

    mu, sigma = _to_mu_sigma(tickers, expected_returns, covariance_matrix)
    n = len(tickers)
    bud = int(budget) if budget is not None else _budget_half_assets(n)
    bud = max(1, min(n, bud))

    portfolio = PortfolioOptimization(mu, sigma, float(risk_factor), bud)
    qp = portfolio.to_quadratic_program()

    sampler = StatevectorSampler()
    cobyla = COBYLA(maxiter=int(cobyla_maxiter))
    qaoa = QAOA(sampler, cobyla, reps=int(qaoa_reps))
    qubo_converter = QuadraticProgramToQubo()
    optimizer = MinimumEigenOptimizer(qaoa, converters=qubo_converter)
    result = optimizer.solve(qp)

    x = np.asarray(result.x, dtype=float).ravel()
    binary = (x >= 0.5).astype(int)

    allocation = {tickers[i]: int(binary[i]) for i in range(n)}
    selected = [tickers[i] for i in range(n) if binary[i] == 1]

    return {
        "tickers": tickers,
        "budget": bud,
        "risk_factor": float(risk_factor),
        "allocation": allocation,
        "selected_tickers": selected,
        "objective_value": float(result.fval),
        "solution_vector": [float(x[i]) for i in range(n)],
        "solver": {
            "name": "MinimumEigenOptimizer",
            "eigensolver": "QAOA",
            "sampler": "StatevectorSampler",
            "qubo_converter": "QuadraticProgramToQubo",
            "qaoa_reps": int(qaoa_reps),
        },
        "quadratic_program": {
            "num_binary_vars": int(qp.get_num_binary_vars()),
            "num_variables": int(qp.get_num_vars()),
        },
    }
