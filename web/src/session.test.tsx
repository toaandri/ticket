import { act, cleanup, render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import type { Tokens } from '../../packages/api-client/src';
import { ApiError, request } from './api';
import { SessionProvider, useSession } from './session';

vi.mock('./api', async importOriginal => ({
  ...await importOriginal<typeof import('./api')>(),
  request: vi.fn(),
}));

const requestMock = vi.mocked(request);
const profile = { id: 'alice', email: 'alice@example.com', display_name: 'Alice', email_verified_at: null };
const initial = { access: 'initial-access', refresh: 'initial-refresh' };
let session: ReturnType<typeof useSession>;
let queries: QueryClient;

function Probe() { session = useSession(); return null; }
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}

beforeEach(async () => {
  requestMock.mockReset();
  requestMock.mockImplementation(async <T,>(path: string): Promise<T> => (path === '/me/' ? profile : initial) as T);
  queries = new QueryClient();
  render(<QueryClientProvider client={queries}><SessionProvider><Probe /></SessionProvider></QueryClientProvider>);
  await act(async () => { await session.login(profile.email, 'password'); });
});
afterEach(() => { cleanup(); queries.clear(); });

it('does not reinstall credentials when a refresh finishes after logout', async () => {
  const rotation = deferred<Tokens>();
  const started = deferred<void>();
  requestMock.mockImplementation(async <T,>(path: string, _options?: RequestInit, access?: string): Promise<T> => {
    if (path === '/auth/refresh/') {
      started.resolve(); return rotation.promise as Promise<T>;
    }
    if (path === '/private/' && access === initial.access) throw new ApiError('Expired', 401);
    return undefined as T;
  });
  const pending = session.api('/private/').catch(error => error);
  await started.promise;
  let logout!: Promise<void>;
  await act(async () => { logout = session.logout(); });
  expect(session.user).toBeNull();
  await act(async () => { rotation.resolve({ access: 'late-access', refresh: 'late-refresh' }); await pending; await logout; });
  expect(session.user).toBeNull();
  await session.api('/public/');
  expect(requestMock).toHaveBeenLastCalledWith('/public/', {}, undefined);
  expect(requestMock.mock.calls.some(([path, , access]) => path === '/private/' && access === 'late-access')).toBe(false);
  expect(requestMock.mock.calls.filter(([path]) => path === '/auth/refresh/')).toHaveLength(1);
  expect(requestMock).toHaveBeenCalledWith('/auth/logout/', expect.objectContaining({ body: JSON.stringify({ refresh: 'late-refresh' }) }), 'late-access');
});

it('keeps a newly signed-in account when an old refresh fails', async () => {
  const rotation = deferred<Tokens>();
  const started = deferred<void>();
  const bob = { ...profile, id: 'bob', email: 'bob@example.com', display_name: 'Bob' };
  requestMock.mockImplementation(async <T,>(path: string, _options?: RequestInit, access?: string): Promise<T> => {
    if (path === '/auth/refresh/') { started.resolve(); return rotation.promise as Promise<T>; }
    if (path === '/private/' && access === initial.access) throw new ApiError('Expired', 401);
    if (path === '/auth/login/') return { access: 'bob-access', refresh: 'bob-refresh' } as T;
    return bob as T;
  });
  const pending = session.api('/private/').catch(error => error);
  await started.promise;
  await act(async () => { await session.login(bob.email, 'password'); });
  await act(async () => { rotation.reject(new ApiError('Revoked', 401)); await pending; });
  expect(session.user?.id).toBe('bob');
  await session.api('/public/');
  expect(requestMock).toHaveBeenLastCalledWith('/public/', {}, 'bob-access');
});

it('keeps the session through a temporary refresh outage and permits retry', async () => {
  let offline = true;
  requestMock.mockImplementation(async <T,>(path: string, _options?: RequestInit, access?: string): Promise<T> => {
    if (path === '/auth/refresh/') {
      if (offline) throw new Error('Network unavailable');
      return { access: 'new-access', refresh: 'new-refresh' } as T;
    }
    if (path === '/private/' && access === initial.access) throw new ApiError('Expired', 401);
    return 'ok' as T;
  });
  await expect(session.api('/private/')).rejects.toThrow('Network unavailable');
  expect(session.user?.id).toBe('alice');
  offline = false;
  await expect(session.api('/private/')).resolves.toBe('ok');
});

it('rejects an old account response instead of exposing it to the next account', async () => {
  const response = deferred<string>();
  const started = deferred<void>();
  requestMock.mockImplementation(async <T,>(path: string): Promise<T> => {
    if (path === '/private/') { started.resolve(); return response.promise as Promise<T>; }
    return (path === '/me/' ? { ...profile, id: 'bob' } : { access: 'bob-access', refresh: 'bob-refresh' }) as T;
  });
  const pending = session.api('/private/').catch(error => error);
  await started.promise;
  await act(async () => { await session.login('bob@example.com', 'password'); });
  response.resolve('Alice private data');
  expect(await pending).toBeInstanceOf(Error);
  expect(session.user?.id).toBe('bob');
});

it('does not finish a pending sign-in after logout', async () => {
  const response = deferred<Tokens>();
  const started = deferred<void>();
  requestMock.mockImplementation(async <T,>(path: string): Promise<T> => {
    if (path === '/auth/login/') { started.resolve(); return response.promise as Promise<T>; }
    return profile as T;
  });
  let pending!: Promise<unknown>;
  await act(async () => { pending = session.login(profile.email, 'password').catch(error => error); });
  await started.promise;
  await act(async () => { await session.logout(); });
  await act(async () => { response.resolve(initial); await pending; });
  expect(session.user).toBeNull();
  await session.api('/public/');
  expect(requestMock).toHaveBeenLastCalledWith('/public/', {}, undefined);
});
