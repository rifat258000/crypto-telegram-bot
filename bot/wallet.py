"""Multi-chain wallet balance lookup using free public RPCs."""

from __future__ import annotations

import asyncio
import logging
import string

import httpx

from bot.http_client import fetch

log = logging.getLogger(__name__)

EVM_CHAINS = {
    # --- Major L1s ---
    "Ethereum": {
        "rpc": "https://ethereum-rpc.publicnode.com",
        "symbol": "ETH",
        "explorer": "https://etherscan.io/address/",
    },
    "BSC": {
        "rpc": "https://bsc-dataseed.binance.org",
        "symbol": "BNB",
        "explorer": "https://bscscan.com/address/",
    },
    "Polygon": {
        "rpc": "https://polygon-bor-rpc.publicnode.com",
        "symbol": "POL",
        "explorer": "https://polygonscan.com/address/",
    },
    "Avalanche": {
        "rpc": "https://api.avax.network/ext/bc/C/rpc",
        "symbol": "AVAX",
        "explorer": "https://snowtrace.io/address/",
    },
    "Fantom": {
        "rpc": "https://rpcapi.fantom.network",
        "symbol": "FTM",
        "explorer": "https://ftmscan.com/address/",
    },
    "Cronos": {
        "rpc": "https://evm.cronos.org",
        "symbol": "CRO",
        "explorer": "https://cronoscan.com/address/",
    },
    "Gnosis": {
        "rpc": "https://rpc.gnosischain.com",
        "symbol": "xDAI",
        "explorer": "https://gnosisscan.io/address/",
    },
    "Celo": {
        "rpc": "https://forno.celo.org",
        "symbol": "CELO",
        "explorer": "https://celoscan.io/address/",
    },
    "Moonbeam": {
        "rpc": "https://rpc.api.moonbeam.network",
        "symbol": "GLMR",
        "explorer": "https://moonbeam.moonscan.io/address/",
    },
    "Aurora": {
        "rpc": "https://mainnet.aurora.dev",
        "symbol": "ETH",
        "explorer": "https://explorer.aurora.dev/address/",
    },
    "Kaia": {
        "rpc": "https://public-en.node.kaia.io",
        "symbol": "KAIA",
        "explorer": "https://kaiascan.io/address/",
    },
    "Metis": {
        "rpc": "https://andromeda.metis.io/?owner=1088",
        "symbol": "METIS",
        "explorer": "https://andromeda-explorer.metis.io/address/",
    },
    # --- L2s ---
    "Arbitrum": {
        "rpc": "https://arb1.arbitrum.io/rpc",
        "symbol": "ETH",
        "explorer": "https://arbiscan.io/address/",
    },
    "Optimism": {
        "rpc": "https://mainnet.optimism.io",
        "symbol": "ETH",
        "explorer": "https://optimistic.etherscan.io/address/",
    },
    "Base": {
        "rpc": "https://mainnet.base.org",
        "symbol": "ETH",
        "explorer": "https://basescan.org/address/",
    },
    "zkSync": {
        "rpc": "https://mainnet.era.zksync.io",
        "symbol": "ETH",
        "explorer": "https://explorer.zksync.io/address/",
    },
    "Linea": {
        "rpc": "https://rpc.linea.build",
        "symbol": "ETH",
        "explorer": "https://lineascan.build/address/",
    },
    "Scroll": {
        "rpc": "https://rpc.scroll.io",
        "symbol": "ETH",
        "explorer": "https://scrollscan.com/address/",
    },
    "Mantle": {
        "rpc": "https://rpc.mantle.xyz",
        "symbol": "MNT",
        "explorer": "https://mantlescan.xyz/address/",
    },
    "Blast": {
        "rpc": "https://rpc.blast.io",
        "symbol": "ETH",
        "explorer": "https://blastscan.io/address/",
    },
    "opBNB": {
        "rpc": "https://opbnb-mainnet-rpc.bnbchain.org",
        "symbol": "BNB",
        "explorer": "https://opbnbscan.com/address/",
    },
    "Mode": {
        "rpc": "https://mainnet.mode.network",
        "symbol": "ETH",
        "explorer": "https://modescan.io/address/",
    },
    "Manta": {
        "rpc": "https://pacific-rpc.manta.network/http",
        "symbol": "ETH",
        "explorer": "https://manta.socialscan.io/address/",
    },
    "Zora": {
        "rpc": "https://rpc.zora.energy",
        "symbol": "ETH",
        "explorer": "https://zorascan.xyz/address/",
    },
}


async def _evm_balance(rpc: str, address: str) -> float | None:
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.post(rpc, json={
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [address, "latest"],
                "id": 1,
            })
            data = r.json()
            if "result" in data:
                return int(data["result"], 16) / 1e18
    except Exception:
        log.debug("EVM balance failed for %s on %s", address, rpc)
    return None


async def _solana_balance(address: str) -> float | None:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post("https://api.mainnet-beta.solana.com", json={
                "jsonrpc": "2.0",
                "method": "getBalance",
                "params": [address],
                "id": 1,
            })
            data = r.json()
            if "result" in data:
                return data["result"]["value"] / 1e9
    except Exception:
        log.debug("Solana balance failed for %s", address)
    return None


async def _btc_balance(address: str) -> float | None:
    try:
        r = await fetch(f"https://blockchain.info/q/addressbalance/{address}")
        if r.status_code == 200 and r.text.strip().isdigit():
            return int(r.text.strip()) / 1e8
    except Exception:
        log.debug("BTC balance failed for %s", address)
    return None


def is_evm_address(text: str) -> bool:
    return text.startswith("0x") and len(text) == 42


def is_solana_address(text: str) -> bool:
    if len(text) < 32 or len(text) > 44:
        return False
    valid = string.ascii_letters + string.digits
    return all(c in valid for c in text)


def is_btc_address(text: str) -> bool:
    if text.startswith(("1", "3", "bc1")) and 25 <= len(text) <= 62:
        valid = string.ascii_letters + string.digits
        return all(c in valid for c in text)
    return False


def detect_address_type(text: str) -> str | None:
    if is_evm_address(text):
        return "evm"
    if is_btc_address(text):
        return "btc"
    if is_solana_address(text):
        return "sol"
    return None


async def get_wallet_balances(address: str) -> str:
    addr_type = detect_address_type(address)
    if not addr_type:
        return ""

    lines = [f"<b>👛 Wallet Balances</b>\n<code>{address}</code>\n"]

    if addr_type == "evm":
        tasks = {}
        for chain_name, info in EVM_CHAINS.items():
            tasks[chain_name] = asyncio.create_task(
                _evm_balance(info["rpc"], address)
            )
        results = {}
        for chain_name, task in tasks.items():
            results[chain_name] = await task

        has_balance = False
        for chain_name, info in EVM_CHAINS.items():
            bal = results.get(chain_name)
            if bal is not None and bal > 0.000001:
                has_balance = True
                lines.append(
                    f"• <b>{chain_name}</b>: {bal:.6f} {info['symbol']}"
                )

        if not has_balance:
            lines.append("<i>No native token balances found on any chain.</i>")

        chain_count = sum(
            1 for b in results.values() if b is not None and b > 0.000001
        )
        lines.append(f"\n<i>Scanned {len(EVM_CHAINS)} chains • "
                      f"Found on {chain_count} chains</i>")
        lines.append(
            f"<a href=\"{EVM_CHAINS['Ethereum']['explorer']}{address}\">View on Etherscan</a>"
        )

    elif addr_type == "btc":
        bal = await _btc_balance(address)
        if bal is not None:
            lines.append(f"• <b>Bitcoin</b>: {bal:.8f} BTC")
        else:
            lines.append("<i>Could not fetch BTC balance.</i>")
        lines.append(
            f"\n<a href=\"https://blockchain.info/address/{address}\">View on Blockchain.info</a>"
        )

    elif addr_type == "sol":
        bal = await _solana_balance(address)
        if bal is not None:
            lines.append(f"• <b>Solana</b>: {bal:.6f} SOL")
        else:
            lines.append("<i>Could not fetch SOL balance.</i>")
        lines.append(
            f"\n<a href=\"https://solscan.io/account/{address}\">View on Solscan</a>"
        )

    return "\n".join(lines)
