# defi_scanner.py - Extracted and adapted from uploaded files
from __future__ import annotations

import os
import time
import json
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Set

import requests

# ================== CONFIG ================== #
SORT_MODE: str = "ror"  # one of: "apy", "apr", "tvl", "ror"
MIN_APY: float = 5.0
MIN_TVL: float = 500_000
MIN_LIQUIDITY: float = 100_000

# Chains
ALL_CHAINS: Set[str] = {"solana", "bsc", "eth", "sui", "tao", "arbitrum", "optimism", "base"}

# Focused protocols
FOCUS_PROTOCOLS: Set[str] = {
    "beefy", "yearn", "radiant", "aave", "aave-v3", "venus", "morpho",
    "pancakeswap", "raydium", "lido", "marinade", "eigenlayer",
    "kamino", "krystal", "turbo"
}

# Layer2 chains
LAYER2_CHAINS: Set[str] = {"arbitrum", "optimism", "zksync", "base", "scroll", "linea"}

# Mapping protocol -> type
OPPORTUNITY_TYPE_MAP: Dict[str, str] = {
    "beefy": "Vault / Auto-compounding",
    "yearn": "Vault / Auto-compounding",
    "lido": "Staking / Restaking",
    "marinade": "Staking / Restaking",
    "kamino": "Vault / Auto-compounding",
    "krystal": "Vault / Auto-compounding",
    "turbo": "Yield Farming",
    "raydium": "Yield Farming",
    "pancakeswap": "Yield Farming",
    "aave": "Lending / Borrowing",
    "aave-v3": "Lending / Borrowing",
    "venus": "Lending / Borrowing",
    "morpho": "Lending / Borrowing",
    "radiant": "Lending / Borrowing",
    "eigenlayer": "Staking / Restaking",
}

# ================== DATA MODELS ================== #
@dataclass(frozen=True)
class YieldEntry:
    project: str
    chain: str
    apy_str: str
    symbol: str
    tvl_str: str
    risk: str
    pool_id: str
    ror: float
    type: str

    def apy_value(self) -> float:
        try:
            return float(self.apy_str.replace("%", "").strip())
        except Exception:
            return 0.0

    def tvl_value(self) -> float:
        try:
            return float(self.tvl_str.replace("$", "").replace(",", "").strip())
        except Exception:
            return 0.0


@dataclass(frozen=True)
class MemeEntry:
    symbol: str
    chain: str
    price_usd: str
    liquidity_usd: str
    volume_24h_usd: str
    change_24h_pct: str
    risk: str

# ================== UTILITIES ================== #
def safe_request(url: str) -> Dict[str, Any]:
    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        return {"error": str(e)}


def risk_score(apy: float, tvl: float, project: str) -> str:
    pj = project.lower()
    if pj in FOCUS_PROTOCOLS:
        return "Low"
    if tvl > 50_000_000 and apy < 15:
        return "Low"
    if 5_000_000 <= tvl <= 50_000_000 and 15 <= apy <= 50:
        return "Medium"
    if tvl < 5_000_000 or apy > 50:
        return "High"
    return "Medium"


def calc_ror(apy: float, score: str) -> float:
    risk_factor: Dict[str, float] = {"Low": 1.0, "Medium": 0.6, "High": 0.3}
    return apy * risk_factor.get(score, 0.5)


def sort_key(entry: YieldEntry) -> float:
    if SORT_MODE in ["apy", "apr"]:
        return entry.apy_value()
    if SORT_MODE == "tvl":
        return entry.tvl_value()
    return entry.ror

# ================== CORE SCANNERS ================== #
def classify_yield_opportunities() -> Dict[str, List[YieldEntry]]:
    data = safe_request("https://yields.llama.fi/pools")
    if "error" in data:
        print(f"⚠️ yields.llama.fi error: {data['error']}")
        return {"long_term": [], "short_term": [], "focus": [], "layer2": []}

    pools = data.get("data", [])
    if not isinstance(pools, list):
        pools = []

    long_term: List[YieldEntry] = []
    short_term: List[YieldEntry] = []
    focus: List[YieldEntry] = []
    layer2: List[YieldEntry] = []

    for raw in pools:
        if not isinstance(raw, dict):
            continue

        apy_val = raw.get("apy")
        tvl_val = raw.get("tvlUsd", 0)
        project = str(raw.get("project", "") or "")
        chain = str(raw.get("chain", "N/A") or "N/A").lower()
        symbol = str(raw.get("symbol", "N/A") or "N/A")
        pool_id = str(raw.get("pool", "") or "")

        if not isinstance(apy_val, (int, float)) or not isinstance(tvl_val, (int, float)):
            continue

        apy: float = float(apy_val)
        tvl: float = float(tvl_val)

        if apy < MIN_APY or tvl < MIN_TVL:
            continue

        score = risk_score(apy, tvl, project)
        ror = calc_ror(apy, score)
        type_str = OPPORTUNITY_TYPE_MAP.get(project.lower(), "Unknown")

        entry = YieldEntry(
            project=project,
            chain=chain,
            apy_str=f"{apy:.2f}%",
            symbol=symbol,
            tvl_str=f"${tvl:,.0f}",
            risk=score,
            pool_id=pool_id,
            ror=ror,
            type=type_str
        )

        if project.lower() in FOCUS_PROTOCOLS:
            focus.append(entry)
        if score == "Low" and project.lower() not in FOCUS_PROTOCOLS:
            long_term.append(entry)
        elif score != "Low" and project.lower() not in FOCUS_PROTOCOLS:
            short_term.append(entry)
        if chain in LAYER2_CHAINS:
            layer2.append(entry)

    long_term = sorted(long_term, key=sort_key, reverse=True)[:10]
    short_term = sorted(short_term, key=sort_key, reverse=True)[:10]
    layer2 = sorted(layer2, key=sort_key, reverse=True)[:10]
    focus = sorted(focus, key=sort_key, reverse=True)[:10]

    return {"long_term": long_term, "short_term": short_term, "focus": focus, "layer2": layer2}

# ================== MEME COINS ================== #
CHAIN_ID_MAP = {
    1: "eth", 56: "bsc", 101: "sol", 1001: "sui", 108: "tao",
    42161: "arbitrum", 10: "optimism", 8453: "base"
}

MEME_CHAINS: Set[str] = {"sui", "tao", "eth", "bsc", "sol", "base", "optimism", "arbitrum"}

def get_meme_coins() -> List[MemeEntry]:
    queries = ["pepe", "doge", "shiba", "floki", "bonk"]
    results: List[MemeEntry] = []

    for q in queries:
        data = safe_request(f"https://api.dexscreener.com/latest/dex/search?q={q}")
        if "error" in data:
            print(f"⚠️ dexscreener error on query {q}: {data['error']}")
            continue

        pairs = data.get("pairs", [])
        if not isinstance(pairs, list):
            continue

        candidates: List[Tuple[Dict[str, Any], float, float, float]] = []

        for p in pairs:
            if not isinstance(p, dict):
                continue

            chain_id = p.get("chainId", 0)
            chain = CHAIN_ID_MAP.get(chain_id, str(chain_id)).lower()
            if chain not in MEME_CHAINS:
                continue

            liq = float(p.get("liquidity", {}).get("usd", 0) or 0)
            vol24 = float(p.get("volume", {}).get("h24", 0) or 0)
            change24 = float(p.get("priceChange", {}).get("h24", 0) or 0)

            if liq >= MIN_LIQUIDITY and vol24 >= 0.1 * liq:
                candidates.append((p, liq, vol24, change24))

        candidates = sorted(candidates, key=lambda x: x[2], reverse=True)[:3]

        for obj, liq, vol24, change24 in candidates:
            base_token = obj.get("baseToken", {}) if isinstance(obj.get("baseToken", {}), dict) else {}
            symbol = str(base_token.get("symbol", "?") or "?")
            price_usd = str(obj.get("priceUsd", "N/A") or "N/A")

            if change24 > 0 and liq > 1_000_000:
                score = "Low"
            elif change24 < -30:
                score = "High"
            else:
                score = "Medium"

            results.append(
                MemeEntry(
                    symbol=symbol,
                    chain=chain,
                    price_usd=price_usd,
                    liquidity_usd=f"${liq:,.0f}",
                    volume_24h_usd=f"${vol24:,.0f}",
                    change_24h_pct=f"{change24:.2f}%",
                    risk=score,
                )
            )

    return results[:12]  # Return top 12 meme coins

def get_top_picks(all_opportunities: List[YieldEntry]) -> List[YieldEntry]:
    """Get top 5 opportunities by ROR across all categories"""
    return sorted(all_opportunities, key=lambda x: x.ror, reverse=True)[:5]
