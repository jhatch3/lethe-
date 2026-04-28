/**
 * 0G Compute health check — read-only.
 *
 * Prints wallet balance, ledger state, and (if a provider was previously
 * acknowledged) sub-account balance with that provider. No transactions.
 *
 * Run from src/coordinator/scripts/:
 *     npm run check:0g
 */
import { config as loadEnv } from 'dotenv';
import path from 'node:path';
import { ethers } from 'ethers';
import { createZGComputeNetworkBroker } from '@0glabs/0g-serving-broker';

loadEnv({ path: path.resolve(__dirname, '..', '..', '..', '.env') });

const RPC_URL = process.env.ZG_RPC_URL ?? 'https://evmrpc-testnet.0g.ai';
const PRIVATE_KEY = process.env.ZG_PRIVATE_KEY;
const PROVIDER = process.env.LETHE_0G_COMPUTE_PROVIDER;

if (!PRIVATE_KEY) {
  console.error('ERROR: set ZG_PRIVATE_KEY in .env');
  process.exit(1);
}

async function main() {
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  const wallet = new ethers.Wallet(PRIVATE_KEY!, provider);
  const network = await provider.getNetwork();
  const balance = await provider.getBalance(wallet.address);

  console.log('=== Wallet ===');
  console.log(`address  : ${wallet.address}`);
  console.log(`network  : chain ${network.chainId}`);
  console.log(`balance  : ${ethers.formatEther(balance)} OG`);
  if (balance < ethers.parseEther('0.105')) {
    console.log('  ⚠ below 0.105 OG floor — provisioning would fail');
  }

  console.log('\n=== Ledger ===');
  let broker;
  try {
    broker = await createZGComputeNetworkBroker(wallet);
  } catch (e: any) {
    console.log(`broker init failed: ${e?.message ?? e}`);
    return;
  }
  try {
    const ledger = await broker.ledger.getLedger();
    console.log(`total balance     : ${ethers.formatEther(ledger.totalBalance)} OG`);
    console.log(`available balance : ${ethers.formatEther(ledger.availableBalance)} OG`);
  } catch (e: any) {
    const msg = String(e?.message ?? e);
    if (msg.includes('LedgerNotFound') || msg.includes('not exist')) {
      console.log('no ledger yet — run `npm run provision:0g`');
    } else {
      console.log(`ledger query failed: ${msg.slice(0, 200)}`);
    }
  }

  if (PROVIDER) {
    console.log(`\n=== Provider ${PROVIDER.slice(0, 10)}… ===`);
    try {
      const meta = await broker.inference.getServiceMetadata(PROVIDER);
      console.log(`endpoint : ${meta.endpoint}`);
      console.log(`model    : ${meta.model}`);
    } catch (e: any) {
      console.log(`metadata failed: ${String(e?.message ?? e).slice(0, 200)}`);
    }
  } else {
    console.log('\n(set LETHE_0G_COMPUTE_PROVIDER in .env to also check provider metadata)');
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
