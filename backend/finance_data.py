"""
Historical equity data for portfolio optimization (expected returns + covariance).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Typical US equity session count for annualizing daily statistics
TRADING_DAYS_PER_YEAR = 252

_vader: SentimentIntensityAnalyzer | None = None


def _vader_analyzer() -> SentimentIntensityAnalyzer:
    global _vader
    if _vader is None:
        _vader = SentimentIntensityAnalyzer()
    return _vader


def _news_item_text(item: object) -> str:
    """Extract headline + summary from yfinance news (flat or nested ``content``)."""
    if not isinstance(item, dict):
        return ""
    inner = item.get("content")
    if isinstance(inner, dict):
        title = str(inner.get("title") or "")
        summary = str(inner.get("summary") or inner.get("description") or "")
        return f"{title} {summary}".strip()
    title = str(item.get("title") or "")
    summary = str(item.get("summary") or item.get("description") or "")
    return f"{title} {summary}".strip()


def get_news_sentiment(ticker: str) -> float:
    """
    Average VADER compound score (-1..1) over recent Yahoo Finance headlines.
    Returns ``0.0`` when no usable news or on failure.
    """
    sym = str(ticker).strip().upper()
    if not sym:
        return 0.0
    try:
        news = yf.Ticker(sym).news
    except Exception:
        return 0.0
    if not news:
        return 0.0
    analyzer = _vader_analyzer()
    compounds: list[float] = []
    for item in news:
        text = _news_item_text(item)
        if not text:
            continue
        compounds.append(float(analyzer.polarity_scores(text)["compound"]))
    if not compounds:
        return 0.0
    return float(sum(compounds) / len(compounds))


def _download_closes(tickers: list[str], period: str) -> pd.DataFrame:
    raw = yf.download(
        tickers,
        period=period,
        progress=False,
        auto_adjust=True,
        threads=False,
    )
    if raw.empty:
        raise ValueError("No price data returned; verify tickers and period.")
    if "Close" not in raw.columns:
        raise ValueError("Unexpected yfinance payload (missing Close column).")
    close = raw["Close"]
    if isinstance(close, pd.Series):
        return close.to_frame(name=tickers[0])
    return close


def get_stock_data(tickers: list[str], period: str = "1mo") -> dict[str, Any]:
    """
    Download adjusted closing prices and compute sample expected returns (annualized)
    and an annualized covariance matrix from daily log-returns.

    Per-ticker Yahoo news is scored with VADER; annual and daily expected returns are
    scaled by ``(1 + sentiment)`` so negative news lowers the return fed into optimizers.
    Raw statistics are returned under ``expected_returns_*_raw`` keys.

    Parameters
    ----------
    tickers
        Yahoo Finance symbols (e.g. ``AAPL``, ``MSFT``).
    period
        yfinance period string (e.g. ``1mo``, ``3mo``, ``1y``).

    Returns
    -------
    dict
        JSON-serializable summary including ``sentiment_scores``, adjusted ``expected_returns``,
        ``covariance_matrix``, ``correlation_matrix``, ordered ``tickers``, and metadata.
    """
    cleaned = sorted({str(t).strip().upper() for t in tickers if str(t).strip()})
    if not cleaned:
        raise ValueError("tickers must be a non-empty list of symbols.")

    closes = _download_closes(cleaned, period)
    closes = closes.dropna(how="all").sort_index()
    # Align to requested tickers that appeared in columns
    missing_cols = [t for t in cleaned if t not in closes.columns]
    available = [t for t in cleaned if t in closes.columns]
    if not available:
        raise ValueError(f"No columns matched requested tickers: {cleaned}")
    closes = closes[available].dropna(how="any")

    if len(closes) < 2:
        raise ValueError(
            "Need at least two overlapping trading days after cleaning NaNs; "
            "try a longer period or fewer tickers."
        )

    # Daily log-returns for stable covariance / correlation
    log_returns = np.log(closes / closes.shift(1)).dropna(how="any")
    if len(log_returns) < 2:
        raise ValueError("Insufficient return observations for covariance.")

    mu_daily = log_returns.mean()
    cov_daily = log_returns.cov()
    corr = log_returns.corr()

    mu_annual = mu_daily * TRADING_DAYS_PER_YEAR
    cov_annual = cov_daily * TRADING_DAYS_PER_YEAR

    order = list(log_returns.columns)
    cov_list: list[list[float]] = cov_annual.reindex(index=order, columns=order).values.tolist()
    corr_list: list[list[float]] = corr.reindex(index=order, columns=order).values.tolist()

    sentiment_scores: dict[str, float] = {t: get_news_sentiment(t) for t in order}

    mu_annual_raw = {t: float(mu_annual[t]) for t in order}
    mu_daily_raw = {t: float(mu_daily[t]) for t in order}

    expected_returns_annual: dict[str, float] = {}
    expected_returns_daily_adj: dict[str, float] = {}
    for t in order:
        s = sentiment_scores[t]
        factor = 1.0 + s
        expected_returns_annual[t] = mu_annual_raw[t] * factor
        expected_returns_daily_adj[t] = mu_daily_raw[t] * factor

    idx_start = log_returns.index.min()
    idx_end = log_returns.index.max()

    return {
        "tickers": order,
        "period": period,
        "requested_tickers": cleaned,
        "missing_tickers": missing_cols,
        "start_date": idx_start.isoformat() if hasattr(idx_start, "isoformat") else str(idx_start),
        "end_date": idx_end.isoformat() if hasattr(idx_end, "isoformat") else str(idx_end),
        "n_observations": int(len(log_returns)),
        "sentiment_scores": sentiment_scores,
        "expected_returns_raw_annual": mu_annual_raw,
        "expected_returns": expected_returns_annual,
        "expected_returns_daily": expected_returns_daily_adj,
        "expected_returns_daily_raw": mu_daily_raw,
        "covariance_matrix": cov_list,
        "covariance_matrix_annualized": True,
        "correlation_matrix": corr_list,
        "annualization_factor": TRADING_DAYS_PER_YEAR,
        "notes": (
            "Expected returns are annualized mean of daily log-returns × "
            f"{TRADING_DAYS_PER_YEAR}, then multiplied by (1 + VADER sentiment). "
            "Covariance is annualized sample covariance of raw log-returns × "
            f"{TRADING_DAYS_PER_YEAR} (unchanged by sentiment)."
        ),
    }

