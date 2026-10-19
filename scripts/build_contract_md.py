"""
Writes CONTRACT.md from studio-next/live_proof.json (the log prove.ts wrote as it ran), so no transaction hash,
verdict or address in it is ever transcribed by hand.   python3 scripts/build_contract_md.py
Deployment facts come from studio-next/deployment.json (written by hand once, from the deploy logs).
"""
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
L = json.loads((REPO / "studio-next" / "live_proof.json").read_text())
D = json.loads((REPO / "studio-next" / "deployment.json").read_text())
X = "https://explorer-studio-dev.genlayer.com"


def tx(h): return f"[`{h[:10]}…`]({X}/tx/{h})"
def votes(v):
    a, d = v.count("AGREE"), v.count("DISAGREE")
    return f"{a} agree" + (f", {d} disagree" if d else "")
def short(a): return a[:8] + "…" + a[-4:]


regs = [e for e in L if e["step"] == "register" and e["result"] == "FINISHED_WITH_RETURN" and not e["id"].startswith("reg-demo")]
demo_regs = [e for e in L if e["step"] == "register" and e["id"].startswith("reg-demo")]
refusals = [e for e in L if e["step"] == "refuse-register"]
checks = [e for e in L if e["step"] == "check" and not e["args"][0].startswith("demo")]
demo_checks = [e for e in L if e["step"] == "check" and e["args"][0].startswith("demo")]
gates = [e for e in L if e["step"] == "gate"]
read = next((e for e in L if e["step"] == "read"), None)
assert all(e["result"] in ("FINISHED_WITH_RETURN", "FINISHED_WITH_ERROR") for e in L if "result" in e)
decided = [e for e in L if "tx" in e]
dissent = [e for e in decided if "DISAGREE" in e.get("votes", [])]

o = []
w = o.append
w("# TokenOrigin: deployment and live proof\n")
w("## Deployment\n")
w("| | |\n|---|---|")
w("| Network | GenLayer Studio Next, chain 61997 (`chains.studioDevnet`, genlayer-js 2.0.0-rc.1) |")
w(f"| TokenOrigin | [`{D['tokenorigin']['address']}`]({X}/address/{D['tokenorigin']['address']}) - deploy tx {tx(D['tokenorigin']['deploy_tx'])} |")
w(f"| PayoutGate | [`{D['gate']['address']}`]({X}/address/{D['gate']['address']}) - deploy tx {tx(D['gate']['deploy_tx'])}; constructed with TokenOrigin's address, `max_age_seconds` 86400 and a cap of 1,000,000 per token |")
w(f"| PayoutGate (strict) | [`{D['strict']['address']}`]({X}/address/{D['strict']['address']}) - deploy tx {tx(D['strict']['deploy_tx'])}; the same, but wants a check no more than 1 second old (to show a stale check refused) |")
w("| Runner | `py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng` (v0.3.0) |")
w("| Deployer and gate owner | `0x5cdb5699bc1038e115A973bb91A646f7E98C075b` |\n")
w("Both contracts passed the live runner's `getContractSchemaForCode` check before deploying, and **the code on-chain is byte-identical to this repo**: `cd studio-next && npx tsx verify_code.ts <address> <file>` fetches it with `gen_getContractCode` and compares.\n")
w("| Contract | SHA-256 on-chain = SHA-256 of the repo file |\n|---|---|")
w(f"| TokenOrigin / `contracts/token_origin_studio_next.py` | `{D['tokenorigin']['sha256']}` |")
w(f"| PayoutGate / `contracts/payout_gate_studio_next.py` | `{D['gate']['sha256']}` |\n")
w(f"## Live proof ({D['date']})\n")
w(f"Reproduce with `cd studio-next && npx tsx prove.ts <tokenorigin> <register|check|demo|gate|read> [payoutgate] [strict gate]`. Every row is from [`studio-next/live_proof.json`](studio-next/live_proof.json), written as it ran (it resumes where it stopped). \"Agree\" counts the validators that actively voted (Studio Next leaves the rest of the 5-seat committee idle). **All {len(decided)} transactions reached consensus, {len(decided) - len(dissent)} of them with every voting validator agreeing and {len(dissent)} with a dissenting vote (shown as \"disagree\" in the tables)**, including the ones the contracts refused: a refusal is a decided outcome.\n")

w("### 1. Subjects registered\n")
w("Registration is itself a consensus read: every validator fetched the issuer's page, listed the addresses it writes beside the label, and two of the chain's public nodes agreed on what lives at each; at least one must be a token with the registered symbol and decimals. A subject is permissionless and immutable.\n")
w("| Subject | Issuer's page | Label | Chain, symbol, decimals | Tx |\n|---|---|---|---|---|")
for e in regs:
    s = e["subject"]
    w(f"| `{s['subject_id']}` - {e['note']} | {s['docs_url']} | `{s['label']}` | {s['chain']}, {s['symbol']}, {s['decimals']} | {tx(e['tx'])} {votes(e['votes'])} |")

w("\n### 2. What registration refuses\n")
w("| What it tries | Tx | Outcome |\n|---|---|---|")
for e in refusals:
    w(f"| {e['note']} | {tx(e['tx'])} {votes(e['votes'])} | refused: `{e['revert']}` |")

w("\n### 3. The checks: the issuers' tokens and the look-alikes\n")
w("One `verify` is one consensus transaction about one candidate address: every validator reads the issuer's page, lists the addresses it writes by the label, and two of the chain's public nodes agree on what lives at each of those and at the candidate; the language model is asked only how the page presents the candidate, and only if the page lists it. The verdict is plain code on what was agreed.\n")
w("| Check | Subject | Candidate | On-chain (symbol, decimals) | The issuer's page lists | Verdict | Tx |\n|---|---|---|---|---|---|---|")
for e in checks:
    k = e["check"]
    s = k["summary"]
    onchain = f"{s['candidate_symbol']}, {s['candidate_decimals']}" if s["candidate_symbol"] else (s["candidate_kind"] or "").lower()
    listing = ", ".join(f"`{short(a)}`" for a in s["listing"]) or "-"
    why = f" - {k['reasons'][0]}" if k["reasons"] and k["verdict"] not in ("NOT_LISTED",) else ""
    w(f"| {e['note']} | `{k['subject_id']}` | `{short(k['candidate'])}` | {onchain} | {listing} | **{k['verdict']}**{why} | {tx(e['tx'])} {votes(e['votes'])} |")
w("\nThe full address, the listing, the model's reading and the agreed on-chain facts of every row are in the check's record: `get_check(id)`.\n")

if demo_checks:
    w("### 4. Two SYNTHETIC pages, for the verdicts no real page earned\n")
    w("None of the three real issuers' pages marks an address deprecated or not issued by them (the one real `NOT_ISSUER_ISSUED` above is Tether's Kaia address read under a label that names no chain, not a page calling a token bridged; Circle's page does say in prose that some chains' bridged tokens are not Circle-issued, but writes no address for them). To show `DEPRECATED` and `NOT_ISSUER_ISSUED` on-chain, two pages were written for this purpose ([`demo/`](demo/), served from `raw.githubusercontent.com`): they present a fictitious \"Example Issuer\" and name REAL token contracts. **They are not real issuers' pages and no issuer wrote them.**\n")
    w("| Subject | Candidate | The page presents it as | Verdict | Tx |\n|---|---|---|---|---|")
    for e in demo_checks:
        k = e["check"]
        s = k["summary"]
        w(f"| `{k['subject_id']}` | `{short(k['candidate'])}` ({e['note'].replace('SYNTHETIC page: ', '')}) | {s['status'] or '-'} | **{k['verdict']}** | {tx(e['tx'])} {votes(e['votes'])} |")
    w("")

w("### 5. PayoutGate: a consumer that acts on the verdict\n")
w("The gate records a payout approval for a token under a subject only if TokenOrigin's standing for that token is fresh and `CANONICAL`, and the running total stays within the cap. It reads `get_standing` at the moment of the call, from TokenOrigin's own record.\n")
w("| What it shows | Gate | Call | Outcome | Tx |\n|---|---|---|---|---|")
for e in gates:
    subject, token, amount = e["args"]
    out_ = "**recorded**" if e["result"] == "FINISHED_WITH_RETURN" else f"refused: `{e['revert']}`"
    w(f"| {e['note']} | {e['which']} | `approve({subject}, {short(token)}, {int(amount):,})` | {out_} | {tx(e['tx'])} {votes(e['votes'])} |")
if read and read.get("gate_config"):
    cfg = read["gate_config"]
    w(f"\nAfter the run the gate's `get_config()` reports {cfg['approval_count']} approval(s); each is logged with the token, chain, symbol and the issuer's page it relied on (`get_approvals`).")
w("")

w("## What the live run found\n")
for t in D.get("found_live", []):
    w("- " + t)
w("")
if D.get("superseded"):
    w("## Superseded deployments\n")
    w("| Contract | Address | Why it is superseded |\n|---|---|---|")
    for s in D["superseded"]:
        w(f"| {s['contract']} | `{s['address']}` | {s['why']} |")
    w("")
w("## Proven in tests, not live\n")
w("Direct Mode proves these on the captured pages and chain facts (and on edited copies of them, marked SYNTHETIC in the tests); none has a live transaction:\n")
w("- **The consensus boundary**: a validator rejecting a leader whose listing, on-chain facts or reading differ from its own, and accepting an honest one. Direct Mode runs the validator function against changed inputs; the live run shows the committee's votes on an honest leader.")
w("- **Every format refusal** not listed in section 2, and the page-url, label, symbol and decimals rules.")
w("- **Nodes failing in every way, and the order they are asked in**: one to three of the five down or rate-limited (the next is asked instead), four down (refused), a node that lies about what lives at an address, one whose revert is worded differently, one that answers with an error beside a result, a bytes32 symbol, an EIP-7702 wallet: the chain read's fail-closed branches.")
w("- **The address rules**: an address one character too long, glued to a letter, inside a link, in another case; the radius, the nearest-first order and the caps.")
w("- **Tether's two contracts with the symbol USDT beside one label** (Ethereum's and the address the page gives for Kaia) with a reader that tells them apart, EUR₮ beside 'Ethereum', and **Paxos's supply controller**: real, and in the tests; the live run covers the same pages.")
w("- **The gate's age rule for a check dated in the future, and a total exactly at the cap**; the owner-only rule (every live call came from the owner). PayoutGate's logic after its read of TokenOrigin is also run in Direct Mode against a stand-in with `get_standing`'s exact shape; the live section shows the same refusals against the real contract.")
w("- The language model is never run in Direct Mode: it is replaced by a reader that says what the page presents. What the live run shows is the real validators' models classifying the addresses, with the votes in the tables above.")
(REPO / "CONTRACT.md").write_text("\n".join(o) + "\n")
print("wrote CONTRACT.md,", len(o), "lines;", len(decided), "transactions")
