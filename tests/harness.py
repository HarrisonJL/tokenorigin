"""
The world the contract can reach, for Direct Mode: issuer pages (GET) and JSON-RPC nodes (POST) answered from
the captured fixtures, and a stand-in for the validators' language model.

genlayer-test's web mocks match a URL only, but a JSON-RPC node is one URL answering many questions, so the
tests install a handler (Direct Mode's `_live_web_handler` / `_live_llm_handler` hooks) that reads the request
body like a node would. Everything it serves is real captured data (scripts/capture_fixtures.py); a scenario
that needs something the real world did not do edits one field of a real response and says so.
"""

import json
import pathlib
import re

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
CHAIN = json.loads((FIXTURES / "chain.json").read_text())
NODES = {name: tuple(urls) for name, urls in CHAIN["nodes"].items()}
STATE = CHAIN["chains"]            # chain -> address -> [kind, symbol, decimals], as the nodes agreed

PAGES = {
    "https://developers.circle.com/stablecoins/usdc-contract-addresses": "page_circle.html",
    "https://tether.to/en/supported-protocols/": "page_tether.html",
    "https://docs.paxos.com/guides/stablecoin/pyusd/mainnet": "page_paxos.html",
}
CIRCLE, TETHER, PAXOS = list(PAGES)

# Real addresses the tests refer to.
USDC_ETH = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDC_ARB = "0xaf88d065e77c8cc2239327c5edb3a432268e5831"
USDC_E_ARB = "0xff970a61a04b1ca14834a43f5de4533ebddb5cc8"      # Arbitrum's bridged USDC: symbol() also says "USDC"
USDC_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
USDBC_BASE = "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca"       # Base's bridged USDC
USDT_ETH = "0xdac17f958d2ee523a2206206994597c13d831ec7"
EURT_ETH = "0xc581b735a1688071a1746c968e0798d642ede491"
PYUSD_ETH = "0x6c3ea9036406852006290770bedfcaba0e23a0e8"
DAI_ETH = "0x6b175474e89094c44da98b954eedeac495271d0f"
WALLET = "0x000000000000000000000000000000000000dead"           # no code at all: an ordinary account
DELEGATED = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"        # a wallet that has delegated to code (EIP-7702): code, but no symbol()


def page_bytes(url: str) -> bytes:
    return (FIXTURES / PAGES[url]).read_bytes()


def _abi_string(text: str) -> str:
    raw = text.encode("utf-8")
    padded = raw + b"\x00" * (-len(raw) % 32)
    return "0x" + (32).to_bytes(32, "big").hex() + len(raw).to_bytes(32, "big").hex() + padded.hex()


class Node:
    """One node. Real data by default; a field can be bent to make it fail or lie."""

    def __init__(self):
        self.down = False            # connection refused
        self.status = 200            # HTTP status of every answer
        self.junk = False            # answers with something that is not JSON
        self.rpc_error = False       # answers every call with a JSON-RPC error that is not a revert
        self.view = {}               # address -> [kind, symbol, decimals] this node reports instead of the real one
        self.bytes32 = set()         # addresses whose symbol() this node returns as a bytes32
        self.revert_error = (3, "execution reverted")      # how this node words a revert
        self.call_error = None       # (code, message): eth_call answers with this error, which is not a revert
        self.getcode_revert = False  # eth_getCode answers with a revert
        self.also_error = False      # puts an error object beside every real result
        self.no_result = False       # answers with neither a result nor an error
        self.code_override = {}      # address -> the string eth_getCode returns instead of code
        self.call_also_error = None  # (code, message): eth_call answers carry this error beside their result
        self.call_no_result = False  # eth_call answers with neither a result nor an error
        self.calls = 0


class World:
    def __init__(self, chain="ethereum"):
        self.chain = chain
        self.pages = {}              # url -> (status, bytes)
        self.page_down = set()       # urls whose connection fails
        self.nodes = {c: {url: Node() for url in urls} for c, urls in NODES.items()}
        self.state = {c: {a: list(v) for a, v in addrs.items()} for c, addrs in STATE.items()}   # editable copy
        self.reader = None           # callable(chain, symbol, address, contexts) -> dict | str | None
        self.reader_calls = 0
        self.prompts = []

    def serve(self, url: str, body=None, status: int = 200):
        self.pages[url] = (status, page_bytes(url) if body is None else (body.encode() if isinstance(body, str) else body))

    def node(self, chain: str, i: int) -> Node:
        return list(self.nodes[chain].values())[i]

    # --- Nodes ---------------------------------------------------------------

    def _chain_of(self, url: str) -> str:
        for chain, urls in NODES.items():
            if url in urls:
                return chain
        raise KeyError(url)

    def _answer(self, chain: str, node: Node, request: dict):
        method, params = request["method"], request["params"]
        if node.rpc_error:
            return {"jsonrpc": "2.0", "id": 1, "error": {"code": -32005, "message": "rate limit exceeded"}}
        if node.no_result:
            return {"jsonrpc": "2.0", "id": 1}
        address = (params[0] if method == "eth_getCode" else params[0]["to"]).lower()
        kind, symbol, decimals = node.view.get(address) or self.state[chain].get(address) or ["EOA", "", 0]
        revert = {"jsonrpc": "2.0", "id": 1, "error": {"code": node.revert_error[0], "message": node.revert_error[1]}}
        if method == "eth_getCode":
            if node.getcode_revert:
                return revert
            if address in node.code_override:
                return {"jsonrpc": "2.0", "id": 1, "result": node.code_override[address]}
            return {"jsonrpc": "2.0", "id": 1, "result": "0x" if kind == "EOA" else "0x6080604052" + "00" * 16}
        if method == "eth_call":
            selector = params[0]["data"]
            if kind == "EOA":
                return {"jsonrpc": "2.0", "id": 1, "result": "0x"}
            if node.call_error is not None:
                return {"jsonrpc": "2.0", "id": 1, "error": {"code": node.call_error[0], "message": node.call_error[1]}}
            if kind == "CONTRACT" or (kind == "SYMBOL_ONLY" and selector == "0x313ce567") or (kind == "DECIMALS_ONLY" and selector == "0x95d89b41"):
                return revert
            if selector == "0x95d89b41":
                if address in node.bytes32:
                    return {"jsonrpc": "2.0", "id": 1, "result": "0x" + symbol.encode("utf-8").ljust(32, b"\x00").hex()}
                return {"jsonrpc": "2.0", "id": 1, "result": _abi_string(symbol)}
            if selector == "0x313ce567":
                return {"jsonrpc": "2.0", "id": 1, "result": "0x" + decimals.to_bytes(32, "big").hex()}
        return {"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "method not found"}}

    # --- The hooks Direct Mode calls ---------------------------------------------

    def handle(self, data: dict):
        url, method = data["url"], data.get("method", "GET")
        if method == "POST":
            try:
                chain = self._chain_of(url)
            except KeyError:
                return {"ok": {"response": {"status": 404, "headers": {}, "body": b""}}}
            node = self.nodes[chain][url]
            node.calls += 1
            if node.down:
                raise ConnectionError("connection refused")
            if node.junk:
                return {"ok": {"response": {"status": 200, "headers": {}, "body": b"<html>gateway error</html>"}}}
            body = data["body"]
            request = json.loads(body.decode() if isinstance(body, bytes) else body)
            answer = self._answer(chain, node, request)
            if node.also_error:
                answer["error"] = {"code": -32000, "message": "an error beside a result"}
            if request["method"] == "eth_call":
                if node.call_also_error is not None and "result" in answer:
                    answer["error"] = {"code": node.call_also_error[0], "message": node.call_also_error[1]}
                if node.call_no_result:
                    answer = {"jsonrpc": "2.0", "id": 1}
            return {"ok": {"response": {"status": node.status, "headers": {}, "body": json.dumps(answer).encode()}}}
        if url in self.page_down:
            raise ConnectionError("connection refused")
        status, body = self.pages.get(url, (404, b""))
        return {"ok": {"response": {"status": status, "headers": {}, "body": body}}}

    def llm(self, data: dict):
        prompt = data["prompt"]
        self.prompts.append(prompt)
        self.reader_calls += 1
        symbol, chain = re.search(r"Token: (\S+) on (\S+)\. Page:", prompt).groups()
        listing = prompt.split("--- BEGIN UNTRUSTED PAGE TEXT ---\n")[1].split("\n--- END UNTRUSTED PAGE TEXT ---")[0]
        contexts = [re.sub(r"^\[\d+\] ", "", line) for line in listing.split("\n")]
        address = re.search("«(0x[0-9a-fA-F]{40})»", contexts[0]).group(1).lower()
        return {"ok": self.reader(chain, symbol, address, contexts) if self.reader else None}

    def install(self, direct_vm):
        direct_vm._live_web_handler = self.handle
        direct_vm._live_llm_handler = self.llm


def status_reader(status="CURRENT", **per_address):
    """A reader that says the page presents an address as `status` (or as per_address[address])."""
    def read(chain, symbol, address, contexts):
        return {"status": per_address.get(address, status)}
    return read
