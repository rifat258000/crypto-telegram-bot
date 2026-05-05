"""Multi-chain wallet balance lookup using free public RPCs."""

from __future__ import annotations

import asyncio
import logging
import string

import httpx

from bot.http_client import fetch

log = logging.getLogger(__name__)

# balanceOf(address) selector
BALANCE_OF_SEL = "0x70a08231"

# Major tokens to check per chain (contract, symbol, decimals)
CHAIN_TOKENS: dict[str, list[tuple[str, str, int]]] = {
    "Ethereum": [
        ("0xdAC17F958D2ee523a2206206994597C13D831ec7", "USDT", 6),
        ("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "USDC", 6),
        ("0x6B175474E89094C44Da98b954EedeAC495271d0F", "DAI", 18),
        ("0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", "WBTC", 8),
        ("0x514910771AF9Ca656af840dff83E8264EcF986CA", "LINK", 18),
        ("0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984", "UNI", 18),
        ("0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCFeBB0", "MATIC", 18),
        ("0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE", "SHIB", 18),
        ("0x6982508145454Ce325dDbE47a25d4ec3d2311933", "PEPE", 18),
    ],
    "BSC": [
        ("0x55d398326f99059fF775485246999027B3197955", "USDT", 18),
        ("0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", "USDC", 18),
        ("0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3", "DAI", 18),
        ("0x2170Ed0880ac9A755fd29B2688956BD959F933F8", "ETH", 18),
        ("0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c", "BTCB", 18),
        ("0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56", "BUSD", 18),
        ("0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82", "CAKE", 18),
    ],
    "Polygon": [
        ("0xc2132D05D31c914a87C6611C10748AEb04B58e8F", "USDT", 6),
        ("0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "USDC", 6),
        ("0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063", "DAI", 18),
        ("0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619", "WETH", 18),
        ("0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6", "WBTC", 8),
    ],
    "Arbitrum": [
        ("0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", "USDT", 6),
        ("0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "USDC", 6),
        ("0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1", "DAI", 18),
        ("0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f", "WBTC", 8),
        ("0x912CE59144191C1204E64559FE8253a0e49E6548", "ARB", 18),
    ],
    "Base": [
        ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "USDC", 6),
        ("0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb", "DAI", 18),
    ],
    "Optimism": [
        ("0x94b008aA00579c1307B0EF2c499aD98a8ce58e58", "USDT", 6),
        ("0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", "USDC", 6),
        ("0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1", "DAI", 18),
        ("0x4200000000000000000000000000000000000042", "OP", 18),
    ],
    "Avalanche": [
        ("0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7", "USDT", 6),
        ("0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E", "USDC", 6),
        ("0xd586E7F844cEa2F87f50152665BCbc2C279D8d70", "DAI", 18),
    ],
    "Fantom": [
        ("0x04068DA6C83AFCFA0e13ba15A6696662335D5B75", "USDC", 6),
        ("0x049d68029688eAbF473097a2fC38ef61633A3C7A", "fUSDT", 6),
        ("0x8D11eC38a3EB5E956B052f67Da8Bdc9bef8Abf3E", "DAI", 18),
    ],
    "Gnosis": [
        ("0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83", "USDC", 6),
        ("0x4ECaBa5870353805a9F068101A40E0f32ed605C6", "USDT", 6),
    ],
}

EVM_CHAINS = {
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


async def _token_balance(
    rpc: str, token_contract: str, wallet: str
) -> int:
    padded = wallet[2:].lower().zfill(64)
    data = BALANCE_OF_SEL + padded
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.post(rpc, json={
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{"to": token_contract, "data": data}, "latest"],
                "id": 1,
            })
            result = r.json()
            if "result" in result and result["result"] not in ("0x", "0x0"):
                return int(result["result"], 16)
    except Exception:
        log.debug("Token balance failed for %s on %s", token_contract, rpc)
    return 0


async def _get_chain_tokens(
    rpc: str, chain_name: str, address: str
) -> list[tuple[str, float]]:
    tokens = CHAIN_TOKENS.get(chain_name, [])
    if not tokens:
        return []

    tasks = []
    for contract, symbol, decimals in tokens:
        tasks.append(
            (symbol, decimals, asyncio.create_task(
                _token_balance(rpc, contract, address)
            ))
        )

    found = []
    for symbol, decimals, task in tasks:
        raw = await task
        if raw > 0:
            balance = raw / (10 ** decimals)
            if balance > 0.001:
                found.append((symbol, balance))
    return found


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


async def _solana_tokens(address: str) -> list[tuple[str, float]]:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post("https://api.mainnet-beta.solana.com", json={
                "jsonrpc": "2.0",
                "method": "getTokenAccountsByOwner",
                "params": [
                    address,
                    {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                    {"encoding": "jsonParsed"},
                ],
                "id": 1,
            })
            data = r.json()
            accounts = (data.get("result") or {}).get("value") or []
            found = []
            for acc in accounts:
                info = (acc.get("account", {}).get("data", {})
                        .get("parsed", {}).get("info", {}))
                amount_info = info.get("tokenAmount", {})
                ui_amount = amount_info.get("uiAmount")
                if ui_amount and ui_amount > 0.001:
                    mint = info.get("mint", "")
                    found.append((mint[:8] + "…", ui_amount))
            return found[:20]
    except Exception:
        log.debug("Solana token accounts failed for %s", address)
    return []


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


def _fmt_bal(n: float) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.2f}K"
    if n >= 1:
        return f"{n:,.2f}"
    return f"{n:.6f}"


async def get_wallet_balances(address: str) -> str:
    addr_type = detect_address_type(address)
    if not addr_type:
        return ""

    lines = [f"<b>👛 Wallet Balances</b>\n<code>{address}</code>\n"]

    if addr_type == "evm":
        # Query native + token balances in parallel for all chains
        native_tasks = {}
        token_tasks = {}
        for chain_name, info in EVM_CHAINS.items():
            native_tasks[chain_name] = asyncio.create_task(
                _evm_balance(info["rpc"], address)
            )
            token_tasks[chain_name] = asyncio.create_task(
                _get_chain_tokens(info["rpc"], chain_name, address)
            )

        native_results = {}
        token_results = {}
        for chain_name in EVM_CHAINS:
            native_results[chain_name] = await native_tasks[chain_name]
            token_results[chain_name] = await token_tasks[chain_name]

        chains_with_balance = 0
        for chain_name, info in EVM_CHAINS.items():
            native_bal = native_results.get(chain_name)
            tokens = token_results.get(chain_name, [])
            has_native = native_bal is not None and native_bal > 0.000001
            has_tokens = len(tokens) > 0

            if has_native or has_tokens:
                chains_with_balance += 1
                lines.append(f"\n<b>━━ {chain_name} ━━</b>")
                if has_native:
                    lines.append(
                        f"  💎 {_fmt_bal(native_bal)} {info['symbol']}"
                    )
                for symbol, bal in tokens:
                    lines.append(f"  🪙 {_fmt_bal(bal)} {symbol}")

        if chains_with_balance == 0:
            lines.append("<i>No balances found on any chain.</i>")

        lines.append(f"\n<i>Scanned {len(EVM_CHAINS)} chains • "
                      f"Found on {chains_with_balance} chains</i>")
        lines.append(
            f"<a href=\"{EVM_CHAINS['Ethereum']['explorer']}{address}\">"
            "View on Etherscan</a>"
        )

    elif addr_type == "btc":
        bal = await _btc_balance(address)
        if bal is not None:
            lines.append(f"  💎 {bal:.8f} BTC")
        else:
            lines.append("<i>Could not fetch BTC balance.</i>")
        lines.append(
            f"\n<a href=\"https://blockchain.info/address/{address}\">"
            "View on Blockchain.info</a>"
        )

    elif addr_type == "sol":
        bal = await _solana_balance(address)
        tokens = await _solana_tokens(address)
        if bal is not None:
            lines.append(f"  💎 {_fmt_bal(bal)} SOL")
        for mint, amount in tokens:
            lines.append(f"  🪙 {_fmt_bal(amount)} ({mint})")
        if bal is None and not tokens:
            lines.append("<i>Could not fetch SOL balance.</i>")
        lines.append(
            f"\n<a href=\"https://solscan.io/account/{address}\">"
            "View on Solscan</a>"
        )

    return "\n".join(lines)
