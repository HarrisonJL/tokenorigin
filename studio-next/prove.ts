// Reproducible live proof for TokenOrigin. Every step's tx hash, result, votes and the contract's recorded
// output are appended to live_proof.json - the source for CONTRACT.md's tables. Steps already in
// live_proof.json are skipped and each run stops at a time budget, so a stall costs nothing: run the same
// command again.
//
//   npx tsx prove.ts <tokenorigin> <phase> [payoutgate] [strict payoutgate]     (the gates' addresses, or - )
//   phases: register | check | gate | demo | read
//     register  the issuers' real pages, each with its chain, and every refusal registration has
//     check     one consensus read per candidate: the issuer's tokens and the look-alikes
//     gate      PayoutGate approving payouts, and every refusal it has; needs the two gates' addresses
//     demo      SYNTHETIC pages (demo/*.html in the repo) that call one address deprecated and another not issuer-issued
//     read      the final state, for CONTRACT.md
import * as fs from "fs";
import { client, readClient, write, safeJson } from "./lib";

const CIRCLE = "https://developers.circle.com/stablecoins/usdc-contract-addresses";
const TETHER = "https://tether.to/en/supported-protocols/";
const PAXOS = "https://docs.paxos.com/guides/stablecoin/pyusd/mainnet";
const DEMO = "https://raw.githubusercontent.com/HarrisonJL/tokenorigin/main/demo/";

const USDC_ETH = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48";
const USDC_ARB = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831";
const USDC_E_ARB = "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8";
const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const USDBC_BASE = "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA";
const USDT_ETH = "0xdAC17F958D2ee523a2206206994597C13D831ec7";
const USDT_KAIA = "0xd077A400968890Eacc75cdc901F0356c943e4fDb";
const EURT_ETH = "0xC581b735A1688071A1746c968e0798D642EDE491";
const PYUSD_ETH = "0x6c3ea9036406852006290770BEdFcAbA0e23A0e8";
const PYUSD_ARB = "0x46850aD61C2B7d64d08c9C754F45254596696984";
const PAXOS_CONTROLLER = "0x31d9bDEa6F104606C954f8FE6ba614F1BD347Ec3";
const DAI_ETH = "0x6B175474E89094C44Da98b954EedeAC495271d0F";
const BURN = "0x000000000000000000000000000000000000dEaD";
// SYNTHETIC: a made-up address with USDC's first and last four characters on Ethereum (0xa0b8...eb48).
const LOOKALIKE = "0xa0b8" + "de".repeat(14) + "ad".repeat(2) + "eb48";

// [subject id, docs page, label, chain, symbol, decimals, note, what it shows]
type Subject = [string, string, string, string, string, number, string, string];
const SUBJECTS: Subject[] = [
  ["circle-eth", CIRCLE, "Ethereum", "ethereum", "USDC", 6, "Circle USDC on Ethereum", "Circle's USDC address page, the Ethereum row"],
  ["circle-arb", CIRCLE, "Arbitrum", "arbitrum", "USDC", 6, "Circle USDC on Arbitrum", "the Arbitrum row, where the bridged USDC.e also says USDC"],
  ["circle-base", CIRCLE, "Base", "base", "USDC", 6, "Circle USDC on Base", "the Base row, where the bridged copy is USDbC"],
  ["tether-eth", TETHER, "Ethereum", "ethereum", "USDT", 6, "Tether USDT on Ethereum", "Tether's page, by 'Ethereum': EUR₮, USD₮ and CNH₮ are written together"],
  ["tether-any-chain", TETHER, "USD₮ contract address", "ethereum", "USDT", 6, "Tether USDT on Ethereum, label names no chain", "Tether's page, by 'USD₮ contract address' (no chain named): two contracts with symbol USDT on Ethereum"],
  ["paxos-eth", PAXOS, "Ethereum Mainnet", "ethereum", "PYUSD", 6, "Paxos PYUSD on Ethereum", "Paxos's page, where a supply controller sits beside the token"],
  ["paxos-arb", PAXOS, "Arbitrum Mainnet", "arbitrum", "PYUSD", 6, "registered, never checked", "a subject with no check yet (for the gate)"],
];
const DEMO_SUBJECTS: Subject[] = [
  ["demo-arb", DEMO + "example-issuer-arbitrum.html", "Arbitrum", "arbitrum", "USDC", 6, "SYNTHETIC page: lists a native and a bridged token", "a page that lists a native token and says another is bridged, not issued by it"],
  ["demo-eth", DEMO + "example-issuer-ethereum.html", "Ethereum", "ethereum", "DAI", 18, "SYNTHETIC page: calls its Ethereum token deprecated", "a page that calls its listed token deprecated"],
];
// Registrations the contract must refuse: [id, args, what it shows]
const REFUSALS: [string, any[], string][] = [
  ["refuse-label", ["x-label", CIRCLE, "Narnia", "ethereum", "USDC", 6, ""], "a label the page never shows"],
  ["refuse-symbol", ["x-symbol", CIRCLE, "Ethereum", "ethereum", "USDT", 6, ""], "a symbol none of the page's Ethereum addresses has (USDT)"],
  ["refuse-duplicate-decimals", ["x-dec", CIRCLE, "Ethereum", "ethereum", "USDC", 18, ""], "the same page, label, chain and symbol, asked with different decimals"],
  ["refuse-decimals", ["x-dec2", TETHER, "USD\u20ae contract address", "ethereum", "XAUt", 18, ""], "a symbol the page's addresses do have (XAU\u20ae, Tether's gold token) with the wrong decimals (it has 6)"],
  ["refuse-chain", ["x-chain", CIRCLE, "Ethereum", "polygon", "USDC", 6, ""], "a chain TokenOrigin has no nodes for"],
  ["refuse-wrong-chain", ["x-wrong", CIRCLE, "Ethereum", "arbitrum", "USDC", 6, ""], "Circle's Ethereum row asked about as an Arbitrum subject: nothing lives there"],
  ["refuse-duplicate", ["x-dup", CIRCLE, "Ethereum", "ethereum", "USDC", 6, ""], "the same page, label, chain and symbol again"],
  ["refuse-http", ["x-http", "http://developers.circle.com/stablecoins/usdc-contract-addresses", "Ethereum", "ethereum", "USDC", 6, ""], "a page that is not https"],
];
// Checks: [id, subject, candidate, what it shows]
const CHECKS: [string, string, string, string][] = [
  ["canon-circle-eth", "circle-eth", USDC_ETH, "Circle's USDC on Ethereum"],
  ["canon-circle-arb", "circle-arb", USDC_ARB, "Circle's USDC on Arbitrum"],
  ["canon-circle-base", "circle-base", USDC_BASE, "Circle's USDC on Base"],
  ["canon-tether", "tether-eth", USDT_ETH, "Tether's USDT on Ethereum"],
  ["crosschain-tether", "tether-any-chain", USDT_KAIA, "the address Tether's page gives for Kaia: on Ethereum a different contract, also called USDT, lives there"],
  ["canon-paxos", "paxos-eth", PYUSD_ETH, "Paxos's PYUSD on Ethereum"],
  ["usdce-arb", "circle-arb", USDC_E_ARB, "Arbitrum's bridged USDC.e: its symbol() also says USDC, and Circle's page does not list it"],
  ["usdbc-base", "circle-base", USDBC_BASE, "Base's bridged USDbC"],
  ["dai-eth", "circle-eth", DAI_ETH, "DAI, a real token the page does not list"],
  ["eurt-eth", "tether-eth", EURT_ETH, "EUR₮, written on Tether's page beside Ethereum but not a USDT"],
  ["burn-eth", "circle-eth", BURN, "an address with no code at all"],
  ["base-on-eth", "circle-eth", USDC_BASE, "USDC's address on Base, asked about on Ethereum, where nothing lives at it"],
  ["controller", "paxos-eth", PAXOS_CONTROLLER, "Paxos's supply controller: a contract, not a token"],
  ["lookalike", "circle-eth", LOOKALIKE, "SYNTHETIC: a made-up address built to look like USDC's"],
];
// Synthetic-page checks: [id, subject, candidate, what]
const DEMO_CHECKS: [string, string, string, string][] = [
  ["demo-native", "demo-arb", USDC_ARB, "SYNTHETIC page: the native token"],
  ["demo-bridged", "demo-arb", USDC_E_ARB, "SYNTHETIC page: the same page says this one is bridged and not issued by the issuer"],
  ["demo-deprecated", "demo-eth", DAI_ETH, "SYNTHETIC page: calls its Ethereum token deprecated"],
];
// The gate, in order: [id, which gate, subject, token, amount, what it shows]
type GateStep = [string, "gate" | "strict", string, string, string, string];
const GATE_STEPS: GateStep[] = [
  ["g-arb", "gate", "circle-arb", USDC_ARB, "400000", "CANONICAL: approved"],
  ["g-base", "gate", "circle-base", USDC_BASE, "250000", "CANONICAL: approved"],
  ["g-usdce", "gate", "circle-arb", USDC_E_ARB, "1", "the bridged USDC that also says USDC: NOT_LISTED: refused"],
  ["g-lookalike", "gate", "circle-eth", LOOKALIKE, "1", "a look-alike address: refused"],
  ["g-cap", "gate", "circle-arb", USDC_ARB, "700000", "400,000 already approved; 700,000 more would pass the 1,000,000 cap: refused"],
  ["g-nocheck", "gate", "paxos-arb", PYUSD_ARB, "1", "registered, never checked: refused"],
  ["g-ghost", "gate", "ghost", USDC_ETH, "1", "a subject TokenOrigin has never heard of: refused"],
  ["g-stale", "strict", "circle-arb", USDC_ARB, "1", "a gate that wants a check no more than a second old: refused"],
];
const DEMO_GATE_STEPS: GateStep[] = [
  ["g-deprecated", "gate", "demo-eth", DAI_ETH, "1", "DEPRECATED: refused"],
  ["g-bridged", "gate", "demo-arb", USDC_E_ARB, "1", "NOT_ISSUER_ISSUED: refused"],
];

function load(): any[] {
  return fs.existsSync("live_proof.json") ? JSON.parse(fs.readFileSync("live_proof.json", "utf-8")) : [];
}
function log(entry: Record<string, unknown>) {
  const all = load();
  all.push(entry);
  fs.writeFileSync("live_proof.json", JSON.stringify(all, null, 1));
}
const done = (id: string) => load().some((e) => e.id === id);

function revertMessage(tx: any): string {
  const found: string[] = [];
  const walk = (o: any) => {
    if (typeof o === "string") {
      const m = o.match(/(subject refused: [^\n"]*|[^\n"]*refused: [^\n"]*|that page, label, chain and symbol are already[^\n"]*|subject_id [^\n"]*|docs_url must[^\n"]*|chain must be[^\n"]*|candidate must[^\n"]*|only the owner[^\n"]*|amount must[^\n"]*|unknown subject_id)/);
      if (m) found.push(m[0]);
    } else if (o && typeof o === "object") Object.values(o).forEach(walk);
  };
  walk(tx);
  return found[0] ?? "";
}

async function main() {
  const [to, phase, gate, strict] = process.argv.slice(2);
  const c = client();
  const r = readClient();
  const votes = (tx: any) => tx.last_round?.validator_votes_name ?? [];
  const started = Date.now();
  const outOfTime = () => Date.now() - started > 330_000;
  const view = async (address: string, fn: string, args: unknown[] = []) => {
    await new Promise((res) => setTimeout(res, 2200));
    return JSON.parse(safeJson(await r.readContract({ address, functionName: fn, args })));
  };
  const stop = () => console.log("  (time budget reached - run this phase again to continue)");

  const registerAll = async (subjects: Subject[]) => {
    for (const [id, page, label, chain, symbol, decimals, note, shows] of subjects) {
      if (done("reg-" + id)) continue;
      if (outOfTime()) return stop();
      const args = [id, page, label, chain, symbol, decimals, note];
      const { hash, tx } = await write(c, to, "register_subject", args);
      const subject = tx.txExecutionResultName === "FINISHED_WITH_RETURN" ? await view(to, "get_subject", [id]) : null;
      log({ id: "reg-" + id, step: "register", args, note: shows, tx: hash, result: tx.txExecutionResultName, votes: votes(tx), revert: tx.txExecutionResultName === "FINISHED_WITH_ERROR" ? revertMessage(tx) : "", subject });
      console.log(`  register ${id}: ${tx.txExecutionResultName} ${subject ? "" : revertMessage(tx)}`);
    }
  };
  const checkAll = async (checks: typeof CHECKS) => {
    for (const [id, subject, candidate, shows] of checks) {
      if (done("check-" + id)) continue;
      if (outOfTime()) return stop();
      const { hash, tx } = await write(c, to, "verify", [subject, candidate]);
      const state = await view(to, "get_state");
      const rec = await view(to, "get_check", [state.check_count - 1]);
      log({ id: "check-" + id, step: "check", args: [subject, candidate], note: shows, tx: hash, result: tx.txExecutionResultName, votes: votes(tx), check: rec });
      console.log(`     ${id}: ${rec.verdict} ${(rec.reasons ?? []).join("; ")}`);
    }
  };
  const runGate = async (steps: GateStep[]) => {
    for (const [id, which, subject, token, amount, note] of steps) {
      if (done(id)) continue;
      if (outOfTime()) return stop();
      const address = which === "gate" ? gate : strict;
      if (!address || address === "-") { console.log(`  ${id}: needs the ${which} gate's address`); continue; }
      // approve(subject_id, token, amount_raw): the amount is a u256, so it goes as a BigInt.
      const { hash, tx } = await write(c, address, "approve", [subject, token, BigInt(amount)]);
      const message = tx.txExecutionResultName === "FINISHED_WITH_ERROR" ? revertMessage(tx) : "";
      const total = await view(address, "get_total", [subject, token]);
      log({ id, step: "gate", which, args: [subject, token, amount], note, tx: hash, result: tx.txExecutionResultName, votes: votes(tx), revert: message, total });
      console.log(`  approve(${subject}, ${token.slice(0, 10)}…, ${amount}) on ${which} -> ${tx.txExecutionResultName} ${message}`);
    }
  };

  if (phase === "register") {
    await registerAll(SUBJECTS);
    for (const [id, args, note] of REFUSALS) {
      if (done(id)) continue;
      if (outOfTime()) return stop();
      const { hash, tx } = await write(c, to, "register_subject", args);
      const message = tx.txExecutionResultName === "FINISHED_WITH_ERROR" ? revertMessage(tx) : "";
      log({ id, step: "refuse-register", args, note, tx: hash, result: tx.txExecutionResultName, votes: votes(tx), revert: message });
      console.log(`  ${id}: ${tx.txExecutionResultName} ${message}`);
    }
    return process.exit(0);
  }
  if (phase === "check") {
    await checkAll(CHECKS);
    return process.exit(0);
  }
  if (phase === "demo") {
    await registerAll(DEMO_SUBJECTS);
    await checkAll(DEMO_CHECKS);
    await runGate(DEMO_GATE_STEPS);       // needs the gate's address, like the gate phase
    return process.exit(0);
  }
  if (phase === "gate") {
    await runGate(GATE_STEPS);
    return process.exit(0);
  }
  if (phase === "read") {
    const subjects = await view(to, "list_subjects");
    const listings: Record<string, any> = {};
    for (const s of subjects) listings[s.subject_id] = await view(to, "get_listing", [s.subject_id]);
    const standings: Record<string, any> = {};
    for (const [, subject, candidate] of [...CHECKS, ...DEMO_CHECKS]) standings[`${subject}|${candidate.toLowerCase()}`] = await view(to, "get_standing", [subject, candidate]);
    const state = await view(to, "get_state");
    const rules = await view(to, "get_rules");
    const gateConfig = gate && gate !== "-" ? await view(gate, "get_config") : null;
    const approvals = gate && gate !== "-" ? await view(gate, "get_approvals", [0, 20]) : [];
    if (!done("read")) log({ id: "read", step: "read", subjects, listings, standings, state, rules, gate_config: gateConfig, approvals });
    return process.exit(0);
  }
  console.log("phases: register | check | demo | gate | read");
  process.exit(1);
}

main().catch((e) => {
  console.error(e?.shortMessage ?? e?.message ?? e);
  process.exit(1);
});
