# TokenOrigin: deployment and live proof

## Deployment

| | |
|---|---|
| Network | GenLayer Studio Next, chain 61997 (`chains.studioDevnet`, genlayer-js 2.0.0-rc.1) |
| TokenOrigin | [`0xc2f09Eb3E89B3290184BBFDD28D51F8BC225F00A`](https://explorer-studio-dev.genlayer.com/address/0xc2f09Eb3E89B3290184BBFDD28D51F8BC225F00A) - deploy tx [`0xc528dc78…`](https://explorer-studio-dev.genlayer.com/tx/0xc528dc786f318fffcd72464b4005ecd23e7cfa1c84a45110614a36919b33a506) |
| PayoutGate | [`0x415593314252D41F49540E098ace63F8deDA6803`](https://explorer-studio-dev.genlayer.com/address/0x415593314252D41F49540E098ace63F8deDA6803) - deploy tx [`0x5330ac9c…`](https://explorer-studio-dev.genlayer.com/tx/0x5330ac9ccf4781fd2880107cfb8778c12116dba1269bc0753b01914426e7b529); constructed with TokenOrigin's address, `max_age_seconds` 86400 and a cap of 1,000,000 per token |
| PayoutGate (strict) | [`0x72e8C9a2A0c117Ec12857617fe69532f1365b0cd`](https://explorer-studio-dev.genlayer.com/address/0x72e8C9a2A0c117Ec12857617fe69532f1365b0cd) - deploy tx [`0x0b9ff211…`](https://explorer-studio-dev.genlayer.com/tx/0x0b9ff2112242d75c2b9f9b6254e112f342033b04d3990798e2e8fc3e5d036208); the same, but wants a check no more than 1 second old (to show a stale check refused) |
| Runner | `py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng` (v0.3.0) |
| Deployer and gate owner | `0x5cdb5699bc1038e115A973bb91A646f7E98C075b` |

Both contracts passed the live runner's `getContractSchemaForCode` check before deploying, and **the code on-chain is byte-identical to this repo**: `cd studio-next && npx tsx verify_code.ts <address> <file>` fetches it with `gen_getContractCode` and compares.

| Contract | SHA-256 on-chain = SHA-256 of the repo file |
|---|---|
| TokenOrigin / `contracts/token_origin_studio_next.py` | `ee80b494bcd0004905f3c3384118690ad9e07b8f939b84a62b2c2a67bfd2c08c` |
| PayoutGate / `contracts/payout_gate_studio_next.py` | `c86f87204feaa5a6ea86fef743b8bc60fc81352f31a0efb8b0cf836c878ab04e` |

## Live proof (2026-10-19)

Reproduce with `cd studio-next && npx tsx prove.ts <tokenorigin> <register|check|demo|gate|read> [payoutgate] [strict gate]`. Every row is from [`studio-next/live_proof.json`](studio-next/live_proof.json), written as it ran (it resumes where it stopped). "Agree" counts the validators that actively voted (Studio Next leaves the rest of the 5-seat committee idle). **All 37 transactions reached consensus, 37 of them with every voting validator agreeing and 0 with a dissenting vote (shown as "disagree" in the tables)**, including the ones the contracts refused: a refusal is a decided outcome.

### 1. Subjects registered

Registration is itself a consensus read: every validator fetched the issuer's page, listed the addresses it writes beside the label, and two of the chain's public nodes agreed on what lives at each; at least one must be a token with the registered symbol and decimals. A subject is permissionless and immutable.

| Subject | Issuer's page | Label | Chain, symbol, decimals | Tx |
|---|---|---|---|---|
| `circle-eth` - Circle's USDC address page, the Ethereum row | https://developers.circle.com/stablecoins/usdc-contract-addresses | `Ethereum` | ethereum, USDC, 6 | [`0xe7ce7b27…`](https://explorer-studio-dev.genlayer.com/tx/0xe7ce7b27016efab8326c95b958a1361e40c0f8bcb61db0f0639ad6abf40660a4) 3 agree |
| `circle-arb` - the Arbitrum row, where the bridged USDC.e also says USDC | https://developers.circle.com/stablecoins/usdc-contract-addresses | `Arbitrum` | arbitrum, USDC, 6 | [`0x872ffe5d…`](https://explorer-studio-dev.genlayer.com/tx/0x872ffe5d8a91e5751fc95a419a929740ac8d7ad6b58160ebe337bbaf593dff27) 3 agree |
| `circle-base` - the Base row, where the bridged copy is USDbC | https://developers.circle.com/stablecoins/usdc-contract-addresses | `Base` | base, USDC, 6 | [`0xf8599007…`](https://explorer-studio-dev.genlayer.com/tx/0xf8599007ccddb9007726abf1e7a4cb075af3ee9f16919471859f9d4cf88024d0) 3 agree |
| `tether-eth` - Tether's page, by 'Ethereum': EUR₮, USD₮ and CNH₮ are written together | https://tether.to/en/supported-protocols/ | `Ethereum` | ethereum, USDT, 6 | [`0xc3915bb1…`](https://explorer-studio-dev.genlayer.com/tx/0xc3915bb1bb7d33fb3101a832b11c31d5df20c58af198b137b99c675587945af4) 3 agree |
| `tether-any-chain` - Tether's page, by 'USD₮ contract address' (no chain named): two contracts with symbol USDT on Ethereum | https://tether.to/en/supported-protocols/ | `USD₮ contract address` | ethereum, USDT, 6 | [`0x0c48ed8b…`](https://explorer-studio-dev.genlayer.com/tx/0x0c48ed8b6a92fec333accc3194b2476c0de7c263496efd6d6ee21d77e70a261d) 3 agree |
| `paxos-eth` - Paxos's page, where a supply controller sits beside the token | https://docs.paxos.com/guides/stablecoin/pyusd/mainnet | `Ethereum Mainnet` | ethereum, PYUSD, 6 | [`0x67162430…`](https://explorer-studio-dev.genlayer.com/tx/0x671624308dc00f691f2ce7d3cf4c87aa5f9d30ad20fe1cb9e6d7b7c63098fffe) 3 agree |
| `paxos-arb` - a subject with no check yet (for the gate) | https://docs.paxos.com/guides/stablecoin/pyusd/mainnet | `Arbitrum Mainnet` | arbitrum, PYUSD, 6 | [`0x65d0a003…`](https://explorer-studio-dev.genlayer.com/tx/0x65d0a003c53825d7e85470e34979099c1e7bb9765c197e9d9e984d53c3a66466) 3 agree |

### 2. What registration refuses

| What it tries | Tx | Outcome |
|---|---|---|
| a label the page never shows | [`0xd3cdb746…`](https://explorer-studio-dev.genlayer.com/tx/0xd3cdb746266d36afee60553e0c8b7d0feb0333132fb17db0fa0e7be0be4f7191) 3 agree | refused: `subject refused: no_address_near_the_label` |
| a symbol none of the page's Ethereum addresses has (USDT) | [`0x442187e1…`](https://explorer-studio-dev.genlayer.com/tx/0x442187e152acec3ba17517243a0005682b12498039d5af2c488ac5b4e26ac305) 3 agree | refused: `subject refused: no address the page lists near the label is a token with symbol USDT and 6 decimals on ethereum` |
| the same page, label, chain and symbol, asked with different decimals | [`0xae47319a…`](https://explorer-studio-dev.genlayer.com/tx/0xae47319a6c11d559080d3f536dee4ac3fcd76a27d902329222b008784868a3bc) 3 agree | refused: `that page, label, chain and symbol are already registered as 'circle-eth'` |
| a symbol the page's addresses do have (XAU₮, Tether's gold token) with the wrong decimals (it has 6) | [`0x4ecc9cfa…`](https://explorer-studio-dev.genlayer.com/tx/0x4ecc9cfa941466671d83b6452828e240a8a050fcd5dc6a82d7b7c62d038e2e4f) 3 agree | refused: `subject refused: no address the page lists near the label is a token with symbol XAUt and 18 decimals on ethereum` |
| a chain TokenOrigin has no nodes for | [`0x20d1c93e…`](https://explorer-studio-dev.genlayer.com/tx/0x20d1c93e8906e023ea700ae49f511c90cd38f57b2961e27bc7b53e052d7bebe2) 3 agree | refused: `chain must be one of arbitrum, base, ethereum` |
| Circle's Ethereum row asked about as an Arbitrum subject: nothing lives there | [`0xfd375da8…`](https://explorer-studio-dev.genlayer.com/tx/0xfd375da8cc703613dcd63d39ec8e0ba53fb44b0d8f99b98515d4b80da429d88a) 3 agree | refused: `subject refused: no address the page lists near the label is a token with symbol USDC and 6 decimals on arbitrum` |
| the same page, label, chain and symbol again | [`0x0619609f…`](https://explorer-studio-dev.genlayer.com/tx/0x0619609f96c9144397f7310c80f5001927a473305ac6f0b67be7fdcfc1efe2c7) 3 agree | refused: `that page, label, chain and symbol are already registered as 'circle-eth'` |
| a page that is not https | [`0x04fafd6d…`](https://explorer-studio-dev.genlayer.com/tx/0x04fafd6d19e171bd72779db20f895590e292250bbb10982a2611089f97b2ca22) 3 agree | refused: `docs_url must be an https URL on a named host, without a port or fragment` |

### 3. The checks: the issuers' tokens and the look-alikes

One `verify` is one consensus transaction about one candidate address: every validator reads the issuer's page, lists the addresses it writes by the label, and two of the chain's public nodes agree on what lives at each of those and at the candidate; the language model is asked only how the page presents the candidate, and only if the page lists it. The verdict is plain code on what was agreed.

| Check | Subject | Candidate | On-chain (symbol, decimals) | The issuer's page lists | Verdict | Tx |
|---|---|---|---|---|---|---|
| Circle's USDC on Ethereum | `circle-eth` | `0xa0b869…eb48` | USDC, 6 | `0xa0b869…eb48` | **CANONICAL** | [`0xbdeeb7f6…`](https://explorer-studio-dev.genlayer.com/tx/0xbdeeb7f66db93feba27275a9902afcbe7e7ae302f0a91652fd2b66396907836e) 3 agree |
| Circle's USDC on Arbitrum | `circle-arb` | `0xaf88d0…5831` | USDC, 6 | `0xaf88d0…5831` | **CANONICAL** | [`0xa42c683d…`](https://explorer-studio-dev.genlayer.com/tx/0xa42c683d872cd00b527c2fea1e8746cf0cf1254ed027a14313af731222a07a24) 3 agree |
| Circle's USDC on Base | `circle-base` | `0x833589…2913` | USDC, 6 | `0x833589…2913` | **CANONICAL** | [`0x560d2cbc…`](https://explorer-studio-dev.genlayer.com/tx/0x560d2cbc9ecebb07d1d54a9ecdc6e0de0c27ac154fca84307eb2067d6b22be55) 3 agree |
| Tether's USDT on Ethereum | `tether-eth` | `0xdac17f…1ec7` | USDT, 6 | `0xdac17f…1ec7` | **CANONICAL** | [`0xe2482dfc…`](https://explorer-studio-dev.genlayer.com/tx/0xe2482dfc80cdd37c5897404a7e67edae54b9e31d459e36f78e789d09dee8c7f0) 3 agree |
| the address Tether's page gives for Kaia: on Ethereum a different contract, also called USDT, lives there | `tether-any-chain` | `0xd077a4…4fdb` | USDT, 6 | `0xd077a4…4fdb`, `0xdac17f…1ec7` | **NOT_ISSUER_ISSUED** - the issuer's page lists this address as not issued by the issuer | [`0x48ab6aa9…`](https://explorer-studio-dev.genlayer.com/tx/0x48ab6aa9a00d1e48e78d7006f0bcf6c550c24e55cfd220e1509a9084a875e3ed) 3 agree |
| Paxos's PYUSD on Ethereum | `paxos-eth` | `0x6c3ea9…a0e8` | PYUSD, 6 | `0x6c3ea9…a0e8` | **CANONICAL** | [`0x38c0d994…`](https://explorer-studio-dev.genlayer.com/tx/0x38c0d994fd92d8ded159ea9746a71958222fd4214e7b1ca5186ba6b7f26ecd53) 3 agree |
| Arbitrum's bridged USDC.e: its symbol() also says USDC, and Circle's page does not list it | `circle-arb` | `0xff970a…5cc8` | USDC, 6 | `0xaf88d0…5831` | **NOT_LISTED** | [`0xbe588cb7…`](https://explorer-studio-dev.genlayer.com/tx/0xbe588cb7f8d4455626a2101561e60f9d9f385ac9b3181c89fcf5565c39f512b4) 3 agree |
| Base's bridged USDbC | `circle-base` | `0xd9aaec…b6ca` | USDbC, 6 | `0x833589…2913` | **NOT_LISTED** | [`0x9ffb2482…`](https://explorer-studio-dev.genlayer.com/tx/0x9ffb24823bc4d9726f3bcac5d94716161a75a92783a5ccf87375da5248663d47) 3 agree |
| DAI, a real token the page does not list | `circle-eth` | `0x6b1754…1d0f` | DAI, 18 | `0xa0b869…eb48` | **NOT_LISTED** | [`0x1ba61e3c…`](https://explorer-studio-dev.genlayer.com/tx/0x1ba61e3c1c6dedce900f30ac76f7a719317ae34e9e1e70fd5fd5e447de3d4a76) 3 agree |
| EUR₮, written on Tether's page beside Ethereum but not a USDT | `tether-eth` | `0xc581b7…e491` | EURT, 6 | `0xdac17f…1ec7` | **NOT_LISTED** | [`0xb1707294…`](https://explorer-studio-dev.genlayer.com/tx/0xb17072945f5b85e86eea363839ba42d09f9bb3704cfc1fd09af810f02ad2a667) 3 agree |
| an address with no code at all | `circle-eth` | `0x000000…dead` | eoa | `0xa0b869…eb48` | **NOT_A_TOKEN** - no token contract answers at this address on this chain | [`0xf5729907…`](https://explorer-studio-dev.genlayer.com/tx/0xf57299077b5540966d6354d21f754b5bb7a8f39de0a7461f282bfc50c4ed065d) 3 agree |
| USDC's address on Base, asked about on Ethereum, where nothing lives at it | `circle-eth` | `0x833589…2913` | eoa | `0xa0b869…eb48` | **NOT_A_TOKEN** - no token contract answers at this address on this chain | [`0x70bd08cf…`](https://explorer-studio-dev.genlayer.com/tx/0x70bd08cff56867d53b25524fd122ba88418f7d990eab7c4494c8e50540e4cdb6) 3 agree |
| Paxos's supply controller: a contract, not a token | `paxos-eth` | `0x31d9bd…7ec3` | contract | `0x6c3ea9…a0e8` | **NOT_A_TOKEN** - no token contract answers at this address on this chain | [`0x31098df8…`](https://explorer-studio-dev.genlayer.com/tx/0x31098df8b692818ec73b58bd387c839aaa6f0d20b85644154669ed13e410f027) 3 agree |
| SYNTHETIC: a made-up address built to look like USDC's | `circle-eth` | `0xa0b8de…eb48` | eoa | `0xa0b869…eb48` | **LOOKALIKE** - this address shares its first 4 and last 4 characters with the listed 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48 but is a different address | [`0xe402a4e6…`](https://explorer-studio-dev.genlayer.com/tx/0xe402a4e655ec7e7efa74864a870ef5746a77c2de177f31c4a85e0440d57cdbda) 3 agree |

The full address, the listing, the model's reading and the agreed on-chain facts of every row are in the check's record: `get_check(id)`.

### 5. PayoutGate: a consumer that acts on the verdict

The gate records a payout approval for a token under a subject only if TokenOrigin's standing for that token is fresh and `CANONICAL`, and the running total stays within the cap. It reads `get_standing` at the moment of the call, from TokenOrigin's own record.

| What it shows | Gate | Call | Outcome | Tx |
|---|---|---|---|---|
| CANONICAL: approved | gate | `approve(circle-arb, 0xaf88d0…5831, 400,000)` | **recorded** | [`0x313914a8…`](https://explorer-studio-dev.genlayer.com/tx/0x313914a8f91ac14e3670434f898a0845accab35f567628a8dae44e38372b555c) 3 agree |
| CANONICAL: approved | gate | `approve(circle-base, 0x833589…2913, 250,000)` | **recorded** | [`0x713d3f7a…`](https://explorer-studio-dev.genlayer.com/tx/0x713d3f7aa39f56f4a914eb2bd365070b07a9451d62a9f0c3c9e6369e5e09a033) 3 agree |
| the bridged USDC that also says USDC: NOT_LISTED: refused | gate | `approve(circle-arb, 0xFF970A…5CC8, 1)` | refused: `'circle-arb' refused: 0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8 is NOT_LISTED, not CANONICAL` | [`0xfa8ddb64…`](https://explorer-studio-dev.genlayer.com/tx/0xfa8ddb64858e3cf11075054f353ccfde255b92cae7cf32063ffb7bc3090b400e) 3 agree |
| a look-alike address: refused | gate | `approve(circle-eth, 0xa0b8de…eb48, 1)` | refused: `'circle-eth' refused: 0xa0b8dedededededededededededededeadadeb48 is LOOKALIKE, not CANONICAL` | [`0x12f4b5a0…`](https://explorer-studio-dev.genlayer.com/tx/0x12f4b5a0eac2275ac9c7050248680754d8adb6320404beed5ed21ddc7a4363d3) 3 agree |
| 400,000 already approved; 700,000 more would pass the 1,000,000 cap: refused | gate | `approve(circle-arb, 0xaf88d0…5831, 700,000)` | refused: `'circle-arb' refused: this would take the total past the cap 1000000` | [`0x3abfb161…`](https://explorer-studio-dev.genlayer.com/tx/0x3abfb16100ad2f07c6cb81410a31cb02bf95c56f84f87ee033bc36fed722e184) 3 agree |
| registered, never checked: refused | gate | `approve(paxos-arb, 0x46850a…6984, 1)` | refused: `'paxos-arb' refused: no decided check of 0x46850aD61C2B7d64d08c9C754F45254596696984 yet` | [`0xf8f2b403…`](https://explorer-studio-dev.genlayer.com/tx/0xf8f2b40346669d688920683c1676f6dba02a05dc32ba0411626f4b8289847fd3) 3 agree |
| a subject TokenOrigin has never heard of: refused | gate | `approve(ghost, 0xA0b869…eB48, 1)` | refused: `'ghost' refused: TokenOrigin has no such subject` | [`0x75b42875…`](https://explorer-studio-dev.genlayer.com/tx/0x75b4287514ef814aea8ee7845654b9844697ad5093916d74d34ac528a6d3d28b) 3 agree |
| a gate that wants a check no more than a second old: refused | strict | `approve(circle-arb, 0xaf88d0…5831, 1)` | refused: `'circle-arb' refused: its latest decided check of 0xaf88d065e77c8cC2239327C5EDb3A432268e5831 is 317 seconds old; this gate wants at most 1` | [`0x6ad75452…`](https://explorer-studio-dev.genlayer.com/tx/0x6ad75452dc7e756cdee661452b5b488faac5849f88932cc65d31f911654586b8) 3 agree |

## What the live run found

- **Circle's, Tether's and Paxos's own pages named the right token on every chain they were asked about.** USDC on Ethereum, Arbitrum and Base, USDT on Ethereum and PYUSD on Ethereum were each `CANONICAL`: the page writes the address by the chain's name, the chain's nodes agree it is a token with that symbol and those decimals, and the reader, with every voting validator agreeing, said the page presents it as current.
- **The bridged copies that also say "USDC" are not Circle's.** On Arbitrum, USDC.e answers `symbol()` with USDC and `decimals()` with 6, exactly like the native token, and is `NOT_LISTED`: the page lists 0xaf88… for Arbitrum. On Base, the bridged USDbC is `NOT_LISTED` too, and so are DAI and Tether's EUR₮ (written on Tether's page beside Ethereum, but a different token).
- **A look-alike and the non-tokens.** A made-up address built with the first and last four characters of USDC's is `LOOKALIKE` of USDC's listed address (marked SYNTHETIC in the proof; nothing lives there). The burn address, and USDC's Base address asked about on Ethereum, are `NOT_A_TOKEN`, and so is Paxos's supply controller: a contract the page writes beside PYUSD, which is not a token.
- **A label that names no chain puts another chain's address in the listing.** Registered against Tether's "USD₮ contract address", the Ethereum listing held 0xdac1… and 0xd077…, the address the page gives for Kaia, where on Ethereum a different contract named "Tether USD" (symbol USDT, 6 decimals) lives. The reader saw only the Kaia wording around the address and recorded `NOT_ISSUER_ISSUED` with every voting validator agreeing; the lesson is to name the chain, as `tether-eth` does. The recorded reason ("the issuer's page lists this address as not issued by the issuer") is the contract's fixed wording for that verdict, and is looser than what happened here.
- **The gate acts on the verdict.** PayoutGate approved 400,000 of Arbitrum's USDC and 250,000 of Base's, and refused: the bridged USDC.e (`NOT_LISTED`), the look-alike, a payout that would pass the 1,000,000 cap, a token never checked, a subject TokenOrigin has never heard of, and a check older than the strict gate's one second.
- **Registration refuses what the page cannot support.** A label the page never shows, a symbol none of the listed addresses has, an Arbitrum subject registered against the Ethereum row, a duplicate, a chain without nodes, a page that is not https and decimals that do not match were each refused by the validators.
- **The first deployment taught one thing and was replaced.** On it, 1 or 2 of 5 validators dissented on the check of Base's bridged USDbC in roughly four of ten repeated runs: dRPC and Tenderly answered the validators' burst of requests with HTTP 429, so a validator saw fewer than two answers for the address it read last. The verdict was right by majority every time, but a split vote is what a check should not show. The second deployment asks five nodes in order until two have answered; every transaction on it so far was unanimous. See [research/README.md](../research/README.md).

## Superseded deployments

| Contract | Address | Why it is superseded |
|---|---|---|
| TokenOrigin (first deployment) | `0x5d123F8E00631B24E83859Ed4785138EC3A0DEa9` | Deployed earlier the same day (deploy tx 0xe02df85f…). It asked three nodes per chain (dRPC, publicnode, Tenderly) and required all three to answer; under the validators' simultaneous requests two of them returned HTTP 429, which split the vote on the last address read. The code differs in the node lists and the rule for using them (and in the wording of the reader's prompt and two redundant guards removed); its proof is kept in studio-next/live_proof_superseded_v1.json. |

## Proven in tests, not live

Direct Mode proves these on the captured pages and chain facts (and on edited copies of them, marked SYNTHETIC in the tests); none has a live transaction:

- **The consensus boundary**: a validator rejecting a leader whose listing, on-chain facts or reading differ from its own, and accepting an honest one. Direct Mode runs the validator function against changed inputs; the live run shows the committee's votes on an honest leader.
- **Every format refusal** not listed in section 2, and the page-url, label, symbol and decimals rules.
- **Nodes failing in every way, and the order they are asked in**: one to three of the five down or rate-limited (the next is asked instead), four down (refused), a node that lies about what lives at an address, one whose revert is worded differently, one that answers with an error beside a result, a bytes32 symbol, an EIP-7702 wallet: the chain read's fail-closed branches.
- **The address rules**: an address one character too long, glued to a letter, inside a link, in another case; the radius, the nearest-first order and the caps.
- **Tether's two contracts with the symbol USDT beside one label** (Ethereum's and the address the page gives for Kaia) with a reader that tells them apart, EUR₮ beside 'Ethereum', and **Paxos's supply controller**: real, and in the tests; the live run covers the same pages.
- **The gate's age rule for a check dated in the future, and a total exactly at the cap**; the owner-only rule (every live call came from the owner). PayoutGate's logic after its read of TokenOrigin is also run in Direct Mode against a stand-in with `get_standing`'s exact shape; the live section shows the same refusals against the real contract.
- The language model is never run in Direct Mode: it is replaced by a reader that says what the page presents. What the live run shows is the real validators' models classifying the addresses, with the votes in the tables above.
