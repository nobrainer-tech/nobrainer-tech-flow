// Advisor regressions through real SDK clients and the HTTP tool validation path.
import { after, before, describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { Client, InMemoryTransport } from '@modelcontextprotocol/client';
import { body, connect, connectV1, startLocal, TEST_RING } from '../helpers.ts';
import { buildServer } from '../../src/server.ts';
import { memoryLimiter } from '../../src/ratelimit.ts';
import { SNAPSHOT } from '../../src/advisor/snapshot.ts';

for (const era of ['in-memory', 'modern', 'legacy', 'v1'] as const) {
  describe(`advisor SDK regression (${era})`, () => {
    let client: Awaited<ReturnType<typeof connect>> | Awaited<ReturnType<typeof connectV1>>;
    let closeServer: (() => Promise<void>) | undefined;
    before(async () => {
      const now = () => Math.floor(Date.parse(SNAPSHOT.fetched_at) / 1000) + 3600;
      if (era === 'in-memory') {
        const server = buildServer({ ring: TEST_RING, limiter: memoryLimiter(), now });
        const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
        closeServer = () => server.close();
        await server.connect(serverTransport);
        client = new Client({ name: 'advisor-test', version: '1.0.0' }, { versionNegotiation: { mode: 'legacy' } });
        await client.connect(clientTransport);
      } else {
        const local = await startLocal({ now });
        closeServer = local.close;
        client = era === 'v1' ? await connectV1(local.url) : await connect(local.url, era);
      }
    });
    after(async () => {
      await client?.close();
      await closeServer?.();
    });

    test('advertises exactly the canonical tasks with measurement rows', async () => {
      const { tools } = await client.listTools();
      const advisor = tools.find(t => t.name === 'recommend_flow_model');
      assert.ok(advisor);
      const task = advisor.inputSchema.properties?.task as { enum?: string[] };
      assert.ok(Array.isArray(task.enum));
      assert.ok(!task.enum.includes('coding'));
      assert.deepEqual([...task.enum].sort(), [...new Set(SNAPSHOT.table.map(r => r.task))].sort());
    });

    for (const task of ['coding', 'Coding', 'CODING', 'cOdInG', ' Coding ', '\tcOdInG\n']) {
      test(`${JSON.stringify(task)} returns the terminal-coding shortlist`, async () => {
        const call = (task: string) => client.callTool({
          name: 'recommend_flow_model',
          arguments: { task, have: ['openai', 'anthropic'], priority: 'quality' }
        });
        const canonical = await call('terminal-coding');
        assert.notEqual(canonical.isError, true, JSON.stringify(canonical));
        const expected = body(canonical);
        assert.equal(expected.task, 'terminal-coding');
        assert.equal(expected.expired, false);
        assert.ok(expected.shortlist.length > 0, 'canonical shortlist is nonempty');
        for (const entry of expected.shortlist) {
          assert.ok(SNAPSHOT.table.some(row => row.task === 'terminal-coding' &&
            Object.values(SNAPSHOT.byId.get(row.model)?.routes ?? {}).includes(entry.model) &&
            (row.effort === 'default' ? null : row.effort) === entry.effort &&
            Number(row.score.toFixed(1)) === entry.quality), 'shortlist entry has real snapshot evidence');
        }
        const actual = await call(task);
        assert.notEqual(actual.isError, true, JSON.stringify(actual));
        assert.deepEqual(body(actual), expected);
      });
    }
  });
}
