/**
 * One-time 0G Compute Network provisioning script.
 *
 * What it does:
 *   1. Loads ZG_PRIVATE_KEY from .env (a Galileo testnet wallet with OG funds)
 *   2. Creates the broker, deposits 5 OG into the on-chain ledger
 *   3. Lists inference providers, picks the first online one
 *   4. Acknowledges the provider's TEE signer (one-time, mandatory)
 *   5. Funds the provider sub-account from the ledger (1 OG)
 *   6. Prints the endpoint URL + provider address you should paste into .env
 *
 * Run from src/coordinator/scripts/:
 *     npm run provision:0g
 *
 * Get testnet OG: https://faucet.0g.ai/
 */
import { config as loadEnv } from 'dotenv';
import path from 'node:path';
import { ethers } from 'ethers';
import { createZGComputeNetworkBroker } from '@0glabs/0g-serving-broker';

loadEnv({ path: path.resolve(__dirname, '..', '..', '..', '.env') });

const RPC_URL = process.env.ZG_RPC_URL ?? 'https://evmrpc-testnet.0g.ai';
const PRIVATE_KEY = process.env.ZG_PRIVATE_KEY;

if (!PRIVATE_KEY) {
  console.error('ERROR: set ZG_PRIVATE_KEY in your environment (0x-prefixed hex).');
  console.error('Fund the wallet at https://faucet.0g.ai/ before running.');
  process.exit(1);
}

async function main() {
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  const wallet = new ethers.Wallet(PRIVATE_KEY!, provider);
  console.log(`Wallet: ${wallet.address}`);
  const balance = await provider.getBalance(wallet.address);
  console.log(`Balance: ${ethers.formatEther(balance)} OG`);
  if (balance < ethers.parseEther('0.105')) {
    console.error('Need at least ~0.105 OG (0.1 ledger minimum + gas).');
    console.error('Top up via https://cloud.google.com/application/web3/faucet/0g/galileo');
    process.exit(1);
  }

  const broker = await createZGComputeNetworkBroker(wallet);

  // On-chain minimum first-time ledger deposit is 0.1 OG (verified empirically:
  // contract reverts MinimumDepositRequired below that). Sub-account transfer
  // can be smaller — provider docs suggest ~0.005 OG covers a few inferences.
  const DEPOSIT_OG = 0.1;
  const PROVIDER_SUB_OG = 0.005;

  console.log(`Depositing ${DEPOSIT_OG} OG into ledger...`);
  try {
    await broker.ledger.depositFund(DEPOSIT_OG);
  } catch (e) {
    console.log('  depositFund threw — trying addLedger (first-time setup)...');
    await broker.ledger.addLedger(DEPOSIT_OG);
  }
  const ledger = await broker.ledger.getLedger();
  console.log(`  ledger total: ${ethers.formatEther(ledger.totalBalance)} OG`);

  console.log('Listing inference providers...');
  const services = await broker.inference.listService();
  if (services.length === 0) throw new Error('No 0G Compute providers online right now.');
  const svc = services[0];
  console.log(`  picked: ${svc.provider}  (model: ${svc.model})`);

  console.log('Acknowledging provider TEE signer...');
  try {
    await broker.inference.acknowledgeProviderSigner(svc.provider);
  } catch (e: any) {
    if (String(e?.message ?? e).toLowerCase().includes('already')) {
      console.log('  already acknowledged');
    } else {
      throw e;
    }
  }

  console.log(`Funding provider sub-account (${PROVIDER_SUB_OG} OG)...`);
  try {
    await broker.ledger.transferFund(svc.provider, 'inference', ethers.parseEther(String(PROVIDER_SUB_OG)));
  } catch (e: any) {
    console.log(`  transferFund: ${e?.message ?? e}`);
  }

  const meta = await broker.inference.getServiceMetadata(svc.provider);
  console.log('\n=== PASTE THESE INTO .env ===');
  console.log(`LETHE_0G_COMPUTE_ENDPOINT=${meta.endpoint}`);
  console.log(`LETHE_0G_COMPUTE_MODEL=${meta.model}`);
  console.log(`LETHE_0G_COMPUTE_PROVIDER=${svc.provider}`);
  console.log('');
  console.log('NOTE: 0G Compute auth headers are per-request and signed against the');
  console.log('request body hash — there is no long-lived bearer token. Run');
  console.log('`npm run headers:0g` to start a local sidecar that signs each request,');
  console.log('and point LETHE_0G_COMPUTE_ENDPOINT at the sidecar instead of the');
  console.log('provider URL directly.');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
