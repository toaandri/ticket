import type { Tokens } from './index';

export class SessionChangedError extends Error {
  constructor() { super('Session changed. Please try again.'); }
}

/** Keeps token rotation and persistence scoped to the account that started them. */
export class SessionCredentials {
  tokens: Tokens | null = null;
  version = 0;
  private rotating: { version: number; promise: Promise<Tokens> } | null = null;
  private writes: Promise<void> = Promise.resolve();

  constructor(
    private read: () => Promise<string | null> = async () => null,
    private write: (value: string | null) => Promise<void> = async () => {},
  ) {}

  assertCurrent(version: number) {
    if (version !== this.version) throw new SessionChangedError();
  }

  private persist(value: string | null, version: number) {
    // Serialize SecureStore writes: a slow older write must finish before deletion.
    const operation = this.writes.then(async () => {
      if (version === this.version) await this.write(value);
    });
    // Keep the queue usable after failure; the caller still receives the rejection.
    this.writes = operation.catch(() => {});
    return operation;
  }

  clear() {
    this.version += 1;
    this.tokens = null;
    this.rotating = null;
    return this.persist(null, this.version);
  }

  async set(tokens: Tokens, version: number) {
    this.assertCurrent(version);
    await this.persist(tokens.refresh, version);
    this.assertCurrent(version);
    this.tokens = tokens;
  }

  rotate(fetchTokens: (refresh: string) => Promise<Tokens>, version = this.version): Promise<Tokens> {
    this.assertCurrent(version);
    if (this.rotating?.version === version) return this.rotating.promise;
    const operation = (async () => {
      const stored = this.tokens?.refresh ?? await this.read();
      this.assertCurrent(version);
      if (!stored) throw new Error('Please sign in again.');
      const next = await fetchTokens(stored);
      if (version === this.version) {
        await this.persist(next.refresh, version);
        if (version === this.version) this.tokens = next;
      }
      // Logout may still use these tokens for server revocation after local clear.
      return next;
    })();
    const flight = { version, promise: operation.finally(() => {
      if (this.rotating === flight) this.rotating = null;
    }) };
    this.rotating = flight;
    return flight.promise;
  }
}
