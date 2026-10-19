// Keeps the official standings fresh. A consumer wants a decided check no older than a day or so; left alone,
// the official CANONICAL standings age out. This re-verifies each pair (subject, token) that the live proof found
// CANONICAL: one consensus transaction each, in which every validator reads the issuer's page and the chain's
// public nodes. Checks are permissionless, so it signs with a throwaway testnet account created for this run and
// funded from Studio Next's faucet: no stored key, nothing to leak.
//
//   npx tsx refresh.ts [subject ...]      (every canonical pair in live_proof.json, or just those under the subjects named)
import * as crypto from "crypto";
import * as fs from "fs";
import { createAccount, createClient, chains } from "genlayer-js";
import { fees, safeJson, waitDecided, EXPLORER } from "./lib";

const chain: any = (chains as any).studioDevnet;
const deployment = JSON.parse(fs.readFileSync(`${__dirname}/deployment.json`, "utf-8"));
const TOKENORIGIN: string = deployment.tokenorigin.address;
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function rpc(method: string, params: unknown[]) {
  const r = await fetch(chain.rpcUrls.default.http[0], {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  });
  const j: any = await r.json();
  if (j.error) throw new Error(`${method}: ${j.error.message}`);
  return j.result;
}

async function main() {
  const account = createAccount(`0x${crypto.randomBytes(32).toString("hex")}` as `0x${string}`);
  const c: any = createClient({ chain, account });
  await rpc("sim_fundAccount", [account.address, 100000000000000000000]);
  console.log(`throwaway account ${account.address}, funded from the faucet`);

  // Studio Next allows 30 reads a minute: pace them.
  const view = async (address: string, fn: string, args: unknown[] = []) => {
    await sleep(2200);
    return JSON.parse(safeJson(await c.readContract({ address, functionName: fn, args })));
  };
  const proof: any[] = JSON.parse(fs.readFileSync(`${__dirname}/live_proof.json`, "utf-8"));
  const pairs: [string, string][] = proof.filter((e) => e.step === "check" && e.check.verdict === "CANONICAL").map((e) => [e.check.subject_id, e.check.candidate]);
  const only = process.argv.slice(2);
  const todo = pairs.filter(([subject]) => only.length === 0 || only.includes(subject));
  console.log(`TokenOrigin ${TOKENORIGIN}: ${todo.length} canonical pairs`);

  const failed: string[] = [];
  for (const [subject, token] of todo) {
    try {
      const hash = await c.writeContract({ address: TOKENORIGIN, functionName: "verify", args: [subject, token], fees: await fees(c) });
      const tx = await waitDecided(c, hash);
      const ok = String(tx.status) === "5" || String(tx.status) === "7";
      const standing = ok ? await view(TOKENORIGIN, "get_standing", [subject, token]) : null;
      console.log(`${subject} ${token.slice(0, 10)}…: status ${tx.status} ${tx.txExecutionResultName ?? ""} ${standing ? standing.verdict : ""} ${EXPLORER}/tx/${hash}`);
      if (!ok || tx.txExecutionResultName !== "FINISHED_WITH_RETURN") failed.push(`${subject}|${token}`);
    } catch (e: any) {
      console.log(`${subject} ${token.slice(0, 10)}…: ${e?.shortMessage ?? e?.message ?? e}`);
      failed.push(`${subject}|${token}`);
    }
  }
  if (failed.length) {
    console.log(`not refreshed: ${failed.join(", ")}`);
    process.exit(1);
  }
  process.exit(0);
}

main().catch((e) => {
  console.error(e?.shortMessage ?? e?.message ?? e);
  process.exit(1);
});
