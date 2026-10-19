import { client, write } from "../studio-next/lib";
const P = "0xe68c541d584C72E4Cd9Aa747b88c72091db2cf5e";
const TOKENS: Record<string, string> = { ethereum: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", arbitrum: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", base: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913" };
const URLS: Record<string, string[]> = {
  ethereum: ["https://eth.drpc.org", "https://ethereum-rpc.publicnode.com", "https://gateway.tenderly.co/public/mainnet"],
  arbitrum: ["https://arbitrum.drpc.org", "https://arbitrum-one-rpc.publicnode.com", "https://arbitrum.gateway.tenderly.co"],
  base: ["https://base.drpc.org", "https://base-rpc.publicnode.com", "https://base.gateway.tenderly.co"],
};
const body = (method: string, params: unknown[]) => ({ jsonrpc: "2.0", id: 1, method, params });
(async () => {
  const chain = process.argv[2];
  const t = TOKENS[chain];
  const calls: any[] = [];
  for (const url of URLS[chain]) {
    calls.push({ url, body: body("eth_getCode", [t, "latest"]) });
    calls.push({ url, body: body("eth_call", [{ to: t, data: "0x95d89b41" }, "latest"]) });
    calls.push({ url, body: body("eth_call", [{ to: t, data: "0x313ce567" }, "latest"]) });
    calls.push({ url, body: body("eth_call", [{ to: "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", data: "0x95d89b41" }, "latest"]) });   // an EOA
  }
  await write(client(), P, "probe_rpc", [JSON.stringify(calls)]);
  process.exit(0);
})();
