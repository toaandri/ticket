import { expect, it, vi } from 'vitest';
import type { Tokens } from '../../packages/api-client/src';
import { SessionChangedError, SessionCredentials } from '../../packages/api-client/src/session';

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
}
const initial = { access: 'access', refresh: 'refresh' };
const next = { access: 'next-access', refresh: 'next-refresh' };

it('shares one rotation until the rotated refresh credential has been persisted', async () => {
  const saved = deferred<void>();
  const saving = deferred<void>();
  const write = vi.fn(async (value: string | null) => {
    if (value === next.refresh) { saving.resolve(); await saved.promise; }
  });
  const credentials = new SessionCredentials(async () => null, write);
  await credentials.set(initial, credentials.version);
  const fetch = vi.fn(async () => next);
  const first = credentials.rotate(fetch);
  await saving.promise;
  const second = credentials.rotate(fetch);
  expect(second).toBe(first);
  saved.resolve();
  await Promise.all([first, second]);
  expect(fetch).toHaveBeenCalledOnce();
  expect(write.mock.calls.filter(([value]) => value === next.refresh)).toHaveLength(1);
});

it('deletes SecureStore credentials after a slow rotation write finishes', async () => {
  const saved = deferred<void>();
  const saving = deferred<void>();
  let stored: string | null = null;
  const credentials = new SessionCredentials(async () => stored, async value => {
    if (value === next.refresh) { saving.resolve(); await saved.promise; }
    stored = value;
  });
  await credentials.set(initial, credentials.version);
  const rotating = credentials.rotate(async () => next);
  await saving.promise;
  const clearing = credentials.clear();
  expect(credentials.tokens).toBeNull();
  saved.resolve();
  await Promise.all([rotating, clearing]);
  expect(stored).toBeNull();
  expect(credentials.tokens).toBeNull();
});

it('discards a restored credential if the session changed while storage was loading', async () => {
  const stored = deferred<string | null>();
  const credentials = new SessionCredentials(() => stored.promise);
  const fetch = vi.fn(async () => next);
  const rotating = credentials.rotate(fetch).catch(error => error);
  await credentials.clear();
  stored.resolve('old-refresh');
  expect(await rotating).toBeInstanceOf(SessionChangedError);
  expect(fetch).not.toHaveBeenCalled();
});

it('leaves the current account and storage intact when an old rotation completes', async () => {
  const rotated = deferred<Tokens>();
  const write = vi.fn<(value: string | null) => Promise<void>>().mockResolvedValue(undefined);
  const credentials = new SessionCredentials(async () => null, write);
  await credentials.set(initial, credentials.version);
  const rotating = credentials.rotate(() => rotated.promise);
  await credentials.clear();
  const bob = { access: 'bob-access', refresh: 'bob-refresh' };
  await credentials.set(bob, credentials.version);
  rotated.resolve(next);
  await rotating;
  expect(credentials.tokens).toEqual(bob);
  expect(write).toHaveBeenLastCalledWith(bob.refresh);
  expect(write).not.toHaveBeenCalledWith(next.refresh);
});

it('does not publish login credentials if SecureStore fails to persist them', async () => {
  const credentials = new SessionCredentials(async () => null, async () => { throw new Error('Storage unavailable'); });
  await expect(credentials.set(initial, credentials.version)).rejects.toThrow('Storage unavailable');
  expect(credentials.tokens).toBeNull();
});
