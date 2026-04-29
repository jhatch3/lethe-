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
import fs from 'node:fs/promises';
import os from 'node:os';
import crypto from 'node:crypto';
import http from 'node:http';
import { ethers } from 'ethers';
import { Indexer, MemData, defaultUploadOption, Uploader } from '@0glabs/0g-ts-sdk';

// --- Monkey-patch Uploader.submitTransaction ---
// The 0G Galileo Flow contract has been upgraded: the SDK calls submit(Submission)
// (selector 0xef3e12dc), which now reverts. Successful txs use selector 0xbc8c11f8
// with args (Submission, address sender, uint256 length). We rebuild the on-chain
// commit step using a raw call against that selector while keeping the SDK's
// off-chain pipeline (merkle tree, node selection, segment upload) intact.
const NEW_SUBMIT_SELECTOR = '0xbc8c11f8';
const SUBMISSION_ABI = '(uint256,bytes,(bytes32,uint256)[])';
const MARKET_ABI = ['function pricePerSector() view returns (uint256)'];
const FLOW_MARKET_ABI = ['function market() view returns (address)'];

(Uploader.prototype as any).submitTransaction = async function (
  submission: any,
  opts: any,
) {
  const flow = this.flow;
  const provider = this.provider;
  const signer = flow.runner;
  const sender: string = await signer.getAddress();

  const marketAddr: string = await flow.market();
  const market = new ethers.Contract(marketAddr, MARKET_ABI, provider);
  const pricePerSector: bigint = await market.pricePerSector();

  // SDK-equivalent fee: pricePerSector × number of padded sectors.
  // submission.nodes is array of (root, height); each contributes 2^height chunks
  // (256 bytes each); 1 sector = 256 bytes for fee purposes here.
  let totalChunks = 0n;
  for (const n of submission.nodes) {
    totalChunks += 1n << BigInt(n.height);
  }
  const fee: bigint = opts && opts.fee && BigInt(opts.fee) > 0n
    ? BigInt(opts.fee)
    : pricePerSector * totalChunks;

  // Function takes a SINGLE struct arg wrapping (Submission, address, uint256).
  // Verified by decoding successful txs from other submitters on Galileo.
  const coder = ethers.AbiCoder.defaultAbiCoder();
  const encodedArgs = coder.encode(
    [`(${SUBMISSION_ABI},address,uint256)`],
    [[
      [submission.length, submission.tags, submission.nodes.map((n: any) => [n.root, n.height])],
      sender,
      submission.length,
    ]],
  );
  const calldata = NEW_SUBMIT_SELECTOR + encodedArgs.slice(2);
  const feeData = await provider.getFeeData();
  const gasPrice = feeData.gasPrice ?? 4_000_000_000n;

  console.log('Submitting transaction (patched 0xbc8c11f8) with storage fee:', fee.toString());
  try {
    const tx = await signer.sendTransaction({
      to: await flow.getAddress(),
      data: calldata,
      value: fee,
      gasPrice,
    });
    const receipt = await tx.wait();
    return [receipt, null];
  } catch (e: any) {
    return [null, new Error('Failed to submit transaction: ' + (e?.message ?? e))];
  }
};

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

    // GET /download?root=0x... — fetch a previously-uploaded blob by merkle root.
    // The 0G TS SDK's `Indexer.download` writes to disk, so we use a per-request
    // temp file: download → read bytes → return → unlink.
    if (req.method === 'GET' && req.url?.startsWith('/download')) {
      const url = new URL(req.url, `http://localhost:${PORT}`);
      const root = url.searchParams.get('root');
      if (!root) {
        res.writeHead(400, { 'content-type': 'application/json' });
        res.end(JSON.stringify({ ok: false, error: 'missing root query param' }));
        return;
      }
      const tmp = path.join(os.tmpdir(), `lethe-blob-${crypto.randomBytes(8).toString('hex')}`);
      try {
        const dlErr = await indexer.download(root, tmp, true);
        if (dlErr) throw new Error(`indexer.download: ${dlErr.message ?? String(dlErr)}`);
        const buf = await fs.readFile(tmp);
        res.writeHead(200, {
          'content-type': 'application/octet-stream',
          'content-length': String(buf.length),
        });
        res.end(buf);
      } catch (e: any) {
        console.error('storage download error:', e?.message ?? e);
        res.writeHead(502, { 'content-type': 'application/json' });
        res.end(JSON.stringify({ ok: false, error: String(e?.message ?? e) }));
      } finally {
        try { await fs.unlink(tmp); } catch {}
      }
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
