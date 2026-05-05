"""Market data endpoints for portfolio optimization."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.finance_data import get_stock_data
from backend.quantum_finance import optimize_portfolio

router = APIRouter()


class OptimizePortfolioRequest(BaseModel):
    tickers: list[str] = Field(
        ...,
        min_length=2,
        description="Yahoo Finance symbols to consider (e.g. AAPL, MSFT, TSLA).",
    )
    period: str = Field(
        default="1mo",
        description="History window passed to yfinance (see /finance/data).",
    )
    risk_factor: float = Field(
        default=0.5,
        ge=0.0,
        description="Risk–return trade-off for PortfolioOptimization.",
    )


@router.get("/data")
async def finance_market_data(
    tickers: str = Query(
        ...,
        description="Comma-separated Yahoo Finance symbols (e.g. AAPL,MSFT,TSLA).",
        examples=["AAPL,MSFT,TSLA"],
    ),
    period: str = Query(
        "1mo",
        description="yfinance history window (e.g. 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max).",
    ),
):
    """
    Historical closes → annualized expected returns (from daily log-returns) and
    annualized covariance / correlation matrices for portfolio optimization.
    """
    syms = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    try:
        return get_stock_data(syms, period=period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch or process market data: {e}",
        ) from e


@router.post("/optimize")
async def finance_optimize_portfolio(body: OptimizePortfolioRequest):
    """
    Pull live prices, estimate moments, then run QAOA-based discrete portfolio
    selection (binary per asset, budget ≈ half the universe).
    """
    syms = [t.strip().upper() for t in body.tickers if t.strip()]
    if len(syms) < 2:
        raise HTTPException(
            status_code=400,
            detail="Provide at least two distinct tickers.",
        )
    try:
        market = get_stock_data(syms, period=body.period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Market data failed: {e}",
        ) from e

    order = list(market["tickers"])
    mu = market["expected_returns"]
    cov = market["covariance_matrix"]

    try:
        opt = optimize_portfolio(
            order,
            mu,
            cov,
            risk_factor=body.risk_factor,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Quantum optimization failed: {e}",
        ) from e

    return {
        "allocation": opt["allocation"],
        "selected_tickers": opt["selected_tickers"],
        "budget": opt["budget"],
        "risk_factor": opt["risk_factor"],
        "objective_value": opt["objective_value"],
        "market": {
            "period": market["period"],
            "start_date": market["start_date"],
            "end_date": market["end_date"],
            "n_observations": market["n_observations"],
        },
        "solver": opt["solver"],
        "quantum_details": {
            "solution_vector": opt["solution_vector"],
            "quadratic_program": opt["quadratic_program"],
        },
    }
