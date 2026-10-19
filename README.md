# TokenOrigin

**Is this address the issuer's real token on this chain?** A GenLayer Intelligent Contract that sets an issuer's own documentation beside what the chain says about an address. A treasury paying "USDC" on Arbitrum must pay the token Circle issues there, not a bridged copy that also calls itself USDC, and not an address that only looks like it. The issuer's page says which address is theirs; the chain says what lives at an address. TokenOrigin has validators read the page, plain code list the addresses it writes beside the chain's name, independent public nodes say what lives at each, and a model say only how the page *presents* the one you asked about. The verdict is `CANONICAL`, `DEPRECATED`, `NOT_ISSUER_ISSUED`, `NOT_LISTED`, `LOOKALIKE`, `NOT_A_TOKEN` or `UNDETERMINED`, and a consumer contract can gate a payout on it.

| | |
|---|---|
| Network | GenLayer Studio Next (chain 61997) |
| TokenOrigin | [`0xc2f09Eb3E89B3290184BBFDD28D51F8BC225F00A`](https://explorer-studio-dev.genlayer.com/address/0xc2f09Eb3E89B3290184BBFDD28D51F8BC225F00A) |
| PayoutGate (a consumer) | [`0x415593314252D41F49540E098ace63F8deDA6803`](https://explorer-studio-dev.genlayer.com/address/0x415593314252D41F49540E098ace63F8deDA6803) |
| Live proof | [CONTRACT.md](CONTRACT.md): Circle's, Tether's and Paxos's real pages on Ethereum, Arbitrum and Base, the bridged USDC that also says "USDC", a look-alike address, a label that names no chain, two clearly marked synthetic pages for the verdicts no real page earned, and the gate approving and refusing; 44 transactions, every one linked |
| Research | [research/README.md](research/README.md): what the validators can reach, how the issuers' pages write their addresses, and the decisions that followed |
| Tests | 252 Direct Mode tests on the captured pages and chain facts; 200 safety mutations, all killed |

> **A provenance check, not an audit.** TokenOrigin says whether an address is the one an issuer's own page lists for a token on a chain, and what lives there. It does not say a token is safe, solvent, or free of a freeze or blacklist, and it trusts the issuer's page: if the page is wrong or hijacked, so is the answer. What it removes is the other half of the risk: paying a lookalike or a bridged copy because it was the address in the clipboard.

## Why this exists

Every stablecoin issuer publishes its contract addresses, and every chain is full of tokens that call themselves the same thing. Arbitrum's bridged USDC.e answers `symbol()` with "USDC" and `decimals()` with 6, exactly like Circle's native USDC; no on-chain check can tell them apart. Address-poisoning decoys copy the first and last characters of an address the victim has used before, and are usually plain wallets with no token behind them. A treasury paying a vendor, a protocol whitelisting collateral and a UI choosing a default all need the same thing: the issuer's own statement of which address is theirs, checked against the chain, and kept where a contract can read it.

PayMatch, this account's earlier payment verifier, pins a short list of canonical tokens in its source. TokenOrigin reads them from the issuer instead, so the list is the issuer's and can change when the issuer's page does.

## How it decides

**A subject** binds an issuer's documentation page, a *label* that must sit next to the address (the chain's name as the page writes it, e.g. `Arbitrum`), a chain (Ethereum, Arbitrum or Base) and the symbol and decimals the token must have there. Registering is permissionless and immutable, and is itself a consensus read: the page must write at least one address by the label, and at least one such address must be a token with that symbol and decimals on the chain.

**A check** takes any *candidate* address (anyone can ask about any address, as often as they like), in one transaction:

1. **The page.** Every validator fetches it and reduces it to the words a visitor sees. Plain code lists the distinct addresses written within 250 characters of the label, nearest first, at most six.
2. **The chain.** For each of those and the candidate, independent public nodes say whether code lives there and, if so, what `symbol()` and `decimals()` return. Each chain has five (publicnode, a second provider, dRPC, Tenderly and Nodies or Blast, in a fixed order), and they are asked in that order **until two have answered, which must then say the same**: a node that fails (a rate limit, an outage) is skipped for the next, and one that disagrees fails the read. The page's addresses that really are the registered token on the chain form the issuer's **listing**.
3. **The reader.** Only if the candidate is in the listing: the model is shown the places the page writes that one address, with the address marked, and says how the page presents it: the issuer's own *current* token, *deprecated* (legacy, sunset, migrated), *not issuer-issued* (bridged, wrapped, not backed by the issuer, or an address the page gives for a different chain), or *unclear*. It can only move the verdict down, and it never sees or writes an address.
4. **The verdict.** Plain code on what was agreed:

| The candidate is | Verdict |
|---|---|
| in the listing, and the page presents it as current | `CANONICAL` |
| in the listing, and the page presents it as deprecated | `DEPRECATED` |
| in the listing, and the page says it is not the issuer's own token on this chain (bridged, wrapped, or an address it gives for another chain) | `NOT_ISSUER_ISSUED` |
| in the listing, and the page does not make it clear | `UNDETERMINED` |
| not in the listing, but shares its first 4 and last 4 characters with a listed address | `LOOKALIKE` (checked first: the decoy is usually a plain wallet) |
| not in the listing, and nothing token-like lives there on this chain | `NOT_A_TOKEN` |
| not in the listing, and a real contract (perhaps with the same symbol) lives there | `NOT_LISTED` |
| the page, the nodes or the model unreadable or in disagreement, or no listed address is the registered token | `UNDETERMINED` |

The verdict is recomputed from the agreed facts, never taken from the leader. An `UNDETERMINED` check decides nothing: the **standing** a consumer reads is the latest *decided* check of that token under that subject, so a flaky page can neither hide a bad verdict nor invent a good one, and the consumer sees how old it is.

## The calls

| Call | Who | What it does |
|---|---|---|
| `register_subject(subject_id, docs_url, label, chain, symbol, decimals, note)` | anyone | Binds an issuer's page, a label, a chain and the token's symbol and decimals, after a consensus read of both. Refused if the page writes no address by the label, none of those is the registered token on the chain, the same page/label/chain/symbol is already registered, or any format is wrong (https page URL on a named host, a chain TokenOrigin has nodes for, a symbol and decimals as `symbol()` returns them). |
| `verify(subject_id, candidate)` | anyone | One fresh consensus read of the page and the chain about one candidate address; appends a record with the verdict, the listing, what lives at the candidate, the model's reading and the agreed facts. |

Views: `get_standing(subject_id, token)` (the latest decided check of that token, how old it is, the listing and what it was a lookalike of), `get_listing(subject_id)` (the addresses the issuer's page lists, as of the latest check that found them), `get_subject`, `list_subjects`, `get_check`, `get_checks(offset, limit)`, `get_history(subject_id, limit)`, `get_rules`, `get_state`.

## Using it from another contract

```python
to = gl.contract.get_at(0xc2f09Eb3E89B3290184BBFDD28D51F8BC225F00AESS)           # Studio Next syntax
s = to.view().get_standing("circle-arb", token)
if s["verdict"] != "CANONICAL" or s["age_seconds"] > MAX_AGE:
    raise gl.vm.UserError(f"refused: {token} is {s['verdict']}")
```

[`PayoutGate`](contracts/payout_gate.py) is exactly that, as a contract: the treasury owner records a payout approval for a token under a subject only if TokenOrigin's latest decided check of that token is fresh and `CANONICAL`, and the running total stays within a cap. Each approval is logged with the token, chain, symbol and the issuer's page it relied on. It is a consumer, not a wallet: it does not move tokens.

## What this proves, and what it doesn't

| It proves | It does not prove |
|---|---|
| Which addresses an issuer's page wrote beside a chain's name when the validators read it, and how a model classified one of them, agreed by a committee | That the page is complete, current, or has not been tampered with |
| What lives at each address on the chain, agreed to the last digit by independent nodes: no code, a contract that is not a token, or a token with a symbol and decimals | That a token is safe: nothing about freezes, blacklists, upgrades or backing |
| That a candidate is, or is not, one of the addresses the issuer lists for that token | That the issuer is who it says it is: the subject's page is chosen by whoever registered it, and a consumer pins the subjects it trusts |
| That an address copies the first and last characters of a listed one | That an address which does not is safe: a decoy with a different shape is `NOT_LISTED` or `NOT_A_TOKEN`, not `CANONICAL` |

## Known limitations

- **Three chains** (Ethereum, Arbitrum, Base), each through five keyless nodes of which two are asked. Other chains need their own list.
- **Two nodes, not a majority.** The first two nodes to answer must agree, so a single lying or lagging node fails a read (`UNDETERMINED`) instead of changing it, but two providers that lied identically would be believed. Five are listed so that a rate-limited one can be skipped; the live validators did draw HTTP 429s from dRPC and Tenderly while reading Base, which is why those are no longer the first two.
- **The label is the registrant's choice.** The listing is what the page writes within 250 characters of it, so the label should be the chain's name as it appears beside the token's row. A page that writes several tokens' addresses together (Tether's does) is narrowed by the registered symbol and decimals; the registration is refused if that leaves nothing. A label that names no chain (`tether-any-chain` registers Tether's "USD₮ contract address") lists the address the page gives for Kaia too, which on Ethereum is a different contract that also answers to USDT: only the reader separates them, so name the chain.
- **Server-rendered pages only.** An address a browser fills in is not on the page a validator fetches.
- **The model can disagree with itself.** If validators' models classify differently, a majority decides, as in any GenLayer transaction, and a split vote is visible in the transaction. A model that never returns a usable answer yields `UNDETERMINED`.
- **A wallet that has delegated to code (EIP-7702)** has code and no `symbol()`: it reads as a contract that is not a token.
- **Studio Next only.**

## Running it

```bash
python3 -m venv .venv && .venv/bin/pip install genlayer-test==0.29.2 genvm-linter==0.11.0 pytest
.venv/bin/pytest tests -q                       # the contract and gate tests
.venv/bin/genvm-lint check contracts/token_origin.py    # (one file per call)
python3 scripts/mutation_check.py               # every safety mutation must be killed

cd studio-next && npm ci
npx tsx verify_code.ts <address> token_origin_studio_next.py     # on-chain code == this repo
npx tsx refresh.ts                                                # ask for a fresh check of every official standing
python3 ../scripts/capture_fixtures.py          # re-capture the test inputs (network; the tests do not need it)
```

## Repository layout

```
contracts/token_origin.py               tested source (GenVM v0.2.11)
contracts/token_origin_studio_next.py   deployed port (Studio Next), generated by scripts/port_to_studio_next.py
contracts/payout_gate.py                the consumer, and its deployed port
tests/                                  Direct Mode tests, a stand-in world (harness.py), captured pages and chain facts (fixtures/), mutations
demo/                                   two SYNTHETIC pages for the live proof's DEPRECATED and NOT_ISSUER_ISSUED rows
scripts/                                port, mutation check, fixture capture, CONTRACT.md builder
studio-next/                            deploy, live proof (prove.ts, live_proof.json), verify_code.ts, refresh.ts
research/                               what the validators can reach, how the issuers write their addresses, the decisions
```
