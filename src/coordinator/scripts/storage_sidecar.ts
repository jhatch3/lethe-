/**
 * 0G Storage upload sidecar.
 *
 * Long-running HTTP service that accepts a JSON blob via `POST /upload`,
 * uploads it to 0G Storage via the @0glabs/0g-ts-sdk, and returns the
 * Merkle root + on-chain commitment tx hash. The Python coordinator posts
 * audit pattern records here to anchor them in 0G Storage in addition to
 * the on-chain PatternRegistry event.
 *
 * Coordinator config:
 *     LETHE_0G_STORAGE_SIDECAR_URL=http://localhost:8788
 *
 * Run:
 *     npm run storage:0g
 */
import { config as loadEnv } from 'dotenv';
import path from 'node:path';
import http from 'node:http';
import { ethers } from 'ethers';
import { Indexer, MemData, defaultUploadOption } from '@0glabs/0g-ts-sdk';

loadEnv({ path: path.resolve(__dirname, '..', '..', '..', '.env') });

const RPC_URL = process.env.ZG_RPC_URL ?? 'https://evmrpc-testnet.0g.ai';
const PRIVATE_KEY = process.env.ZG_PRIVATE_KEY;
const INDEXER_URL = process.env.ZG_STORAGE_ENDPOINT ?? 'https://indexer-storage-testnet-turbo.0g.ai';
const PORT = Number(process.env.STORAGE_SIDECAR_PORT ?? 8788);

if (!PRIVATE_KEY) throw new Error('set ZG_PRIVATE_KEY');

async function readBody(req: http.IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

async function main() {
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  const wallet = new ethers.Wallet(PRIVATE_KEY!, provider);
  const indexer = new Indexer(INDEXER_URL);

  console.log(`Storage sidecar ready: http://localhost:${PORT}/upload`);
  console.log(`  wallet  : ${wallet.address}`);
  console.log(`  indexer : ${INDEXER_URL}`);
  console.log(`  rpc     : ${RPC_URL}`);

  const server = http.createServer(async (req, res) => {
    if (req.url === '/health') {
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ ok: true, wallet: wallet.address }));
      return;
    }
    if (req.url !== '/upload' || req.method !== 'POST') {
      res.writeHead(404).end('not found');
      return;
    }
    try {
      const body = await readBody(req);
      // Wrap the JSON bytes as in-memory file data — node-safe, no DOM File.
      const buf = Buffer.from(body, 'utf8');
      const file = new MemData(Array.from(buf));
      // indexer.upload selects nodes internally, builds the merkle tree,
      // submits the on-chain commitment, and serves the file. Returns
      // [{txHash, rootHash}, Error | null].
      const [result, uploadErr] = await indexer.upload(
        file,
        RPC_URL,
        wallet,
        defaultUploadOption,
      );
      if (uploadErr) throw new Error(`indexer.upload: ${uploadErr.message ?? String(uploadErr)}`);
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({
        ok: true,
        root_hash: result.rootHash,
        tx_hash: result.txHash,
        bytes: buf.length,
      }));
    } catch (e: any) {
      console.error('storage sidecar error:', e?.message ?? e);
      res.writeHead(502, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ ok: false, error: String(e?.message ?? e) }));
    }
  });

  server.listen(PORT);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
