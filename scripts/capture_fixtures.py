"""
Captures the real inputs the tests run on, byte for byte, with a manifest of where each came from.

  pages   three issuers' own documentation pages, fetched the way a validator fetches them (plain GET,
          user-agent "reqwest"): Circle's USDC contract addresses, Tether's supported protocols, Paxos's PYUSD
          mainnet addresses.
  chain   what Ethereum, Arbitrum and Base say about every address those pages mention, plus a few real
          addresses the tests ask about (bridged USDC, a wallet, DAI...): is there code, and if so what do
          symbol() and decimals() return. Each is read from FIVE independent keyless nodes, and every one that answers must agree.

Usage:  python3 scripts/capture_fixtures.py [pages|chain|all]      (needs network; the tests do not)
"""
import hashlib
import json
import pathlib
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

FIX = pathlib.Path(__file__).resolve().parent.parent / "tests" / "fixtures"
UA = "reqwest"
PAGES = {
    "circle.html": "https://developers.circle.com/stablecoins/usdc-contract-addresses",
    "tether.html": "https://tether.to/en/supported-protocols/",
    "paxos.html": "https://docs.paxos.com/guides/stablecoin/pyusd/mainnet",
}
CHAINS = {                      # the contract's nodes, in the order it asks them
    "ethereum": ["https://ethereum-rpc.publicnode.com", "https://eth-mainnet.public.blastapi.io", "https://eth.drpc.org",
                 "https://gateway.tenderly.co/public/mainnet", "https://eth-pokt.nodies.app"],
    "arbitrum": ["https://arbitrum-one-rpc.publicnode.com", "https://arb1.arbitrum.io/rpc", "https://arbitrum.drpc.org",
                 "https://arbitrum.gateway.tenderly.co", "https://arbitrum-one.public.blastapi.io"],
    "base": ["https://base-rpc.publicnode.com", "https://mainnet.base.org", "https://base.drpc.org",
             "https://base.gateway.tenderly.co", "https://base-mainnet.public.blastapi.io"],
}
# Real addresses the tests ask about that the pages above do not mention.
EXTRAS = [
    "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",   # Arbitrum: bridged USDC (USDC.e); on-chain symbol "USDC"
    "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA",   # Base: bridged USDC (USDbC)
    "0x6B175474E89094C44Da98b954EedeAC495271d0F",   # Ethereum: DAI
    "0xdAC17F958D2ee523a2206206994597C13D831ec7",   # Ethereum: USDT
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",   # Ethereum: USDC
    "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",   # Arbitrum: USDC
    "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",   # Base: USDC
    "0x000000000000000000000000000000000000dEaD",   # an address with no code: the usual burn address
    "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",   # a wallet that has delegated to code (EIP-7702): code is present, symbol() is not
    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",   # Ethereum: WETH
]
ADDR = re.compile(r"0x[0-9a-fA-F]{40}")
SYMBOL, DECIMALS = "0x95d89b41", "0x313ce567"


def rpc(url, method, params):
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                 headers={"content-type": "application/json", "user-agent": UA})
    for attempt in range(4):
        try:
            return json.load(urllib.request.urlopen(req, timeout=40))
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return {"error": "no answer"}


def text_of(result):
    h = result[2:]
    raw = bytes.fromhex(h)
    if len(raw) == 32:
        return raw.rstrip(b"\0").decode("utf-8")
    n = int.from_bytes(raw[32:64], "big")
    return raw[64:64 + n].decode("utf-8")


def view(url, address):
    code = rpc(url, "eth_getCode", [address, "latest"]).get("result")
    if not isinstance(code, str):
        return None
    if code == "0x":
        return ["EOA", "", 0]
    s = rpc(url, "eth_call", [{"to": address, "data": SYMBOL}, "latest"])
    d = rpc(url, "eth_call", [{"to": address, "data": DECIMALS}, "latest"])
    try:
        return ["TOKEN", text_of(s["result"]), int(d["result"], 16)]
    except Exception:
        return ["CONTRACT", "", 0]


def pages():
    out = {}
    for name, url in PAGES.items():
        req = urllib.request.Request(url, headers={"user-agent": UA})
        resp = urllib.request.urlopen(req, timeout=60)
        raw = resp.read()
        (FIX / ("page_" + name)).write_bytes(raw)
        out[name] = {"url": url, "status": resp.status, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                     "captured": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
        print(name, len(raw))
    return out


def chain():
    addrs = set(a.lower() for a in EXTRAS)
    for name in PAGES:
        addrs |= {a.lower() for a in ADDR.findall((FIX / ("page_" + name)).read_text(errors="replace"))}
    out = {"captured": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "nodes": CHAINS, "chains": {}}
    for chain_name, urls in CHAINS.items():
        out["chains"][chain_name] = {}
        for a in sorted(addrs):
            views = [view(u, a) for u in urls]
            answered = [json.dumps(v) for v in views if v is not None]
            assert len(set(answered)) == 1 and len(answered) >= 3, f"nodes disagree about {a} on {chain_name}: {views}"
            out["chains"][chain_name][a] = json.loads(answered[0])
        tokens = {a: v for a, v in out["chains"][chain_name].items() if v[0] == "TOKEN"}
        print(chain_name, len(addrs), "addresses;", len(tokens), "tokens:", sorted({v[1] for v in tokens.values()}))
    (FIX / "chain.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    manifest = json.loads((FIX / "manifest.json").read_text()) if (FIX / "manifest.json").exists() else {}
    if what in ("pages", "all"):
        manifest["pages"] = pages()
    if what in ("chain", "all"):
        chain()
    (FIX / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
