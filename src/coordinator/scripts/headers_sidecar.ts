/**
 * 0G Compute headers sidecar.
 *
 * 0G Compute auth headers are signed against the request body hash and are
 * single-use — there is no long-lived bearer token. This tiny HTTP service
 * proxies OpenAI-compatible chat-completions requests: it accepts the JSON
 * body the coordinator wants to send, asks the broker SDK for fresh signed
 * headers, then forwards to the actual provider endpoint.
 *
 * Coordinator config:
 *     LETHE_0G_COMPUTE_ENDPOINT=http://localhost:8787/v1
 *     LETHE_0G_COMPUTE_TOKEN=any-non-empty-string   # ignored, sidecar signs
 *
 * Run:
 *     npm run headers:0g
 *
 * Env (alongside ZG_PRIVATE_KEY in .env):
 *     LETHE_0G_COMPUTE_PROVIDER  – provider address from provision.ts output
 *     SIDECAR_PORT               – defaults to 8787
 */
import { config as loadEnv } from 'dotenv';
import path from 'node:path';
import http from 'node:http';
import { ethers } from 'ethers';
import { createZGComputeNetworkBroker } from '@0glabs/0g-serving-broker';

loadEnv({ path: path.resolve(__dirname, '..', '..', '..', '.env') });

const RPC_URL = process.env.ZG_RPC_URL ?? 'https://evmrpc-testnet.0g.ai';
const PRIVATE_KEY = process.env.ZG_PRIVATE_KEY;
const PROVIDER = process.env.LETHE_0G_COMPUTE_PROVIDER;
const PORT = Number(process.env.SIDECAR_PORT ?? 8787);

if (!PRIVATE_KEY) throw new Error('set ZG_PRIVATE_KEY');
if (!PROVIDER) throw new Error('set LETHE_0G_COMPUTE_PROVIDER (run provision:0g first)');

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
  const broker = await createZGComputeNetworkBroker(wallet);
  const meta = await broker.inference.getServiceMetadata(PROVIDER!);
  const upstream = meta.endpoint.replace(/\/+$/, '');
  console.log(`Sidecar ready: http://localhost:${PORT}/v1/* → ${upstream}`);

  const server = http.createServer(async (req, res) => {
    if (!req.url?.startsWith('/v1/')) {
      res.writeHead(404).end('not found');
      return;
    }
    try {
      const body = await readBody(req);
      const headers = await broker.inference.getRequestHeaders(PROVIDER!, body);
      const upstreamUrl = upstream + req.url.replace(/^\/v1/, '');
      const upstreamRes = await fetch(upstreamUrl, {
        method: req.method,
        headers: {
          'content-type': 'application/json',
          ...(headers as unknown as Record<string, string>),
        },
        body: body || undefined,
      });
      res.writeHead(upstreamRes.status, {
        'content-type': upstreamRes.headers.get('content-type') ?? 'application/json',
      });
      const upstreamBody = upstreamRes.body;
      if (upstreamBody) {
        const reader = upstreamBody.getReader();
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          res.write(value);
        }
      }
      res.end();
    } catch (e: any) {
      console.error('sidecar error:', e?.message ?? e);
      res.writeHead(502, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ error: { message: String(e?.message ?? e) } }));
    }
  });

  server.listen(PORT);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
