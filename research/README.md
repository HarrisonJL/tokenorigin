# Research notes

What was checked before TokenOrigin was built, what the data showed, and the decisions that followed. Dates are 2026-10-18 and 19 unless stated. Everything here can be re-run: the captured inputs are in [`tests/fixtures/`](../tests/fixtures/), and the probe that asked Studio Next's validators what they can reach is in this folder.

## Is it already done?

The GenLayer portal publishes its accepted Projects (`/api/v1/explorer/`, 213 on 2026-10-18). I searched their descriptions for token-address, contract-address, whitelist, counterfeit, impersonation, phishing and canonical-asset language. Nothing checks an address against an issuer's own documentation. The nearest are:

| Project | What it does | Why it is not this |
|---|---|---|
| TweetChecker | scam patterns in a pasted tweet (fake giveaways, phishing links) | reads a social post, not an issuer's address list, and checks nothing on-chain |
| IdentityOracle | a claimed name, role and handle against evidence pages | people, not contracts |
| Salvage Arbiter | adjudicates fund-recovery claims for a compromised wallet | a dispute process, after the loss |
| Product Authenticity Registry | a seller's claimed origin against an evidence URL | physical goods |
| Domain Risk Manager | submitter whitelisting inside its own domain registry | an allowlist the owner writes, not one the issuer publishes |

This account's own PayMatch pins a short list of canonical tokens in its source; TokenOrigin is the version where the issuer's page is the list. Unaccepted submissions are not visible, so this is a search, not a proof of absence.

## What the validators can reach (step 0)

A throwaway probe contract ([`probe_studio_next.py`](probe_studio_next.py), deployed at `0xe68c541d584C72E4Cd9Aa747b88c72091db2cf5e`) asked Studio Next's validators to POST JSON-RPC to nine public nodes, three for each chain, because a source can answer a validator (a US-region sandbox) differently from a laptop. [`probe_run.ts`](probe_run.ts) sent one transaction per chain ([Ethereum](https://explorer-studio-dev.genlayer.com/tx/0x343fcb9aa695fb1aef954b15acf3cdcd338237326385c5298e7c4eaf9ba11db2), [Arbitrum](https://explorer-studio-dev.genlayer.com/tx/0x3fe4a6708dddaa7c21fe912c2ca45f78dc15abaad9032d584c785a2fd86d9204), [Base](https://explorer-studio-dev.genlayer.com/tx/0xfaebfce96c9b0c28b0c49fec318f5c32fae7f19e99939ee2b575515a788df0d0)); the raw answers are in [`probe_results.json`](probe_results.json).

| Chain | Nodes | What the validators received for a token and for a wallet |
|---|---|---|
| Ethereum | `eth.drpc.org`, `ethereum-rpc.publicnode.com`, `gateway.tenderly.co/public/mainnet` | `eth_getCode` returned the token's code; `symbol()` and `decimals()` answered; a wallet's `symbol()` returned `0x` |
| Arbitrum | `arbitrum.drpc.org`, `arbitrum-one-rpc.publicnode.com`, `arbitrum.gateway.tenderly.co` | the same |
| Base | `base.drpc.org`, `base-rpc.publicnode.com`, `base.gateway.tenderly.co` | the same |

All nine answered with HTTP 200 from the validators. The facts TokenOrigin reads (code present, `symbol()`, `decimals()`) do not change from block to block, so they are read at `latest` and need no archive state; the nodes only have to be alive and independent. JSON-RPC batching was tried and dropped: dRPC's free tier answered a 27-call batch with HTTP 500, Tenderly with 429 and Nodies refuses more than 10 per batch, so each address is asked of each node with single calls (one for a wallet, three for a token).

## How the issuers' pages write their addresses

The three real pages are captured byte for byte in [`tests/fixtures/`](../tests/fixtures/). Read as a visitor sees them, each address sits beside its label:

- **Circle** (`developers.circle.com/stablecoins/usdc-contract-addresses`): a table, one row per chain, mainnet first and testnets second, so "Ethereum" is followed by Ethereum's address and, a few cells on, by Ethereum Sepolia's. Six addresses lie within 250 characters of the label; on Ethereum only one has code.
- **Tether** (`tether.to/en/supported-protocols/`): prose, one block per chain, with several assets side by side and each address inside a link: "EUR₮ contract address: https://etherscan.io/token/0xC581…", "USD₮ contract address: …0xdac1…", "CNH₮ …". By the label "Ethereum" three addresses of three different tokens; by "USD₮ contract address", which names no chain, six, of which **two have the symbol `USDT` on Ethereum**: Tether's own, and `0xd077…`, the address the page gives under *Kaia*. On Ethereum that address holds a different contract (name "Tether USD", symbol `USDT`, 6 decimals), so a label that does not name the chain puts a look-alike into the listing, and only the reader (which sees the "Kaia Blockchain" words around the address) can tell the two apart.
- **Paxos** (`docs.paxos.com/guides/stablecoin/pyusd/mainnet`): a table with a network column and a token column, then a second table of supply-control addresses. By "Ethereum Mainnet" the PYUSD token, and also a **contract that is not a token** (the supply controller).

Across the three pages and three chains, 88 addresses were read from three nodes each and every node agreed on every one (re-read on 2026-10-19 from the five nodes the contract now uses, see below) ([`tests/fixtures/chain.json`](../tests/fixtures/chain.json)). Two real traps shaped the design:

- **Arbitrum's bridged USDC (USDC.e, `0xFF970A…5CC8`) answers `symbol()` with "USDC" and `decimals()` with 6**, exactly like Circle's native token (`0xaf88d0…5831`). Nothing on-chain separates them; only Circle's page does. On Base the bridged copy is USDbC (another symbol), so a symbol check alone would pass on one chain and fail on the other.
- **vitalik.eth's address now has code** (an EIP-7702 delegation: 23 bytes), and no `symbol()`. "Has code" is not "is a contract that is a token", and "no code" is not the same as "a wallet", so the chain facts have three kinds: no code, a contract that is not a token, a token.

## What broke on the first deployment, and the fix

The first deployment asked three nodes per chain (dRPC, publicnode, Tenderly) about every address and required all three to answer. With five validators reading Base at once from the same network, **dRPC and Tenderly answered some requests with HTTP 429**, and a validator that had fewer than two answers for an address read it as `too_few_sources` while the leader had read it fine: 1 or 2 of 5 validators disagreed on the check of Base's USDbC (the address read last, and so the one that met the rate limit) in roughly four of ten repeated runs, and once three of five did, which sent the transaction to another round. The verdict was still right by majority, but a split vote is exactly what a check should not show.

Found by deploying a debug build whose validators printed *why* they dissented (the receipt carries a validator's stderr): `chain problems leader=[] mine=['too_few_sources_for_0xd9aa…']`, with the per-node views `[None, ['TOKEN', 'USDbC', 6], None]` and `STATUS base.drpc.org eth_getCode 429`. Nothing was wrong with the page, the model or the answers; two of three providers had throttled the validators' shared address.

Public nodes were then measured from the validators themselves (a probe contract, 42 requests per node and chain, in one transaction):

| Chain | Every request answered 200 | Throttled |
|---|---|---|
| Base | `mainnet.base.org`, `base-pokt.nodies.app`, `base-mainnet.public.blastapi.io` (and publicnode in earlier runs) | `base.drpc.org`, `base.gateway.tenderly.co` in the run above |
| Arbitrum | `arb1.arbitrum.io/rpc`, `arb-pokt.nodies.app`, `arbitrum-one.public.blastapi.io` | none seen |
| Ethereum | `eth-mainnet.public.blastapi.io` | `eth-pokt.nodies.app` 429 on 6 of 42 |

Others tried from a laptop and dropped: llamarpc (HTTP 525), omniatech (521), blockpi (402), merkle.io and meowrpc (429 within a dozen requests), 1rpc (intermittent 410/429/503).

The fix, in the contract: **five nodes per chain in a fixed order, asked until two have answered**; the order puts the providers that held up under a burst first (publicnode and a second one), then dRPC, Tenderly and the fifth as stand-ins. That is also a third fewer requests per validator. The cost is a weaker agreement rule than "all three must say the same": the first two to answer must agree, so one lying or lagging node still fails the read, but two providers that lie identically would be believed. That is recorded in the README's limitations.

## Decisions

- **The page lists; the chain filters; the model only downgrades.** Plain code takes the addresses the page writes beside the label. The chain says which of them are the registered token (symbol *and* decimals). The model is asked one thing, only about a candidate already in that listing: how does the page present *this* address (current, deprecated, not issuer-issued, unclear)? It never sees or writes an address, so no instruction in a page can add one to the listing.
- **Look-alikes are checked before anything else.** An address-poisoning decoy is usually a plain wallet, so a rule that said "not a token" first would hide the one thing worth saying. A candidate that is not listed but shares its first four and last four hex characters with a listed address is `LOOKALIKE`. Across all 88 real addresses on the three pages no two are look-alikes of each other (a test), and the chance of a random pair is about 2×10⁻¹⁰.
- **The first two nodes to answer must agree.** Not a majority: if the second says a USDC address is a wallet while the first says token, the read fails. A revert is an answer ("not a token"); a rate-limit error is not, and the next node is asked instead.
- **`UNCLEAR` is a real answer.** A model that never gives a usable reply is read as `UNCLEAR`, which fails closed to `UNDETERMINED`. Whether a reading exists is a fact of the listing (it exists exactly when the candidate is listed), so a validator can check that too.
- **Standing is per token.** An `UNDETERMINED` check decides nothing and never hides a verdict; the standing a consumer reads is the latest decided check of that token under that subject.
- **Dropped**: JSON batching (inconsistent across providers), reading at a pinned block (the facts are static), chains beyond three, and following links on the issuer's page to a second page.
