import { act, render, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, expect, jest, test } from '@jest/globals';
import type { Tokens } from '../../../packages/api-client/src';
import { ApiError, getRefresh, request, saveRefresh } from '../api';
import { SessionProvider, useSession } from '../session';

jest.mock('../api', () => {
  class ApiError extends Error {
    status: number;
    constructor(message: string, code: number) { super(message); this.status = code; }
  }
  return { ApiError, getRefresh: jest.fn(), request: jest.fn(), saveRefresh: jest.fn() };
});

const requestMock = jest.mocked(request);
const saveMock = jest.mocked(saveRefresh);
const readMock = jest.mocked(getRefresh);
const profile = { id: 'alice', email: 'alice@example.com', display_name: 'Alice', email_verified_at: null };
const initial = { access: 'access', refresh: 'refresh' };
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
  requestMock.mockReset(); saveMock.mockReset(); readMock.mockReset();
  readMock.mockResolvedValue(null); saveMock.mockResolvedValue(undefined);
  requestMock.mockImplementation(async <T,>(path: string): Promise<T> => (path === '/me/' ? profile : initial) as T);
  queries = new QueryClient();
  await render(<QueryClientProvider client={queries}><SessionProvider><Probe /></SessionProvider></QueryClientProvider>);
  await waitFor(() => expect(session.ready).toBe(true));
  await act(async () => { await session.login(profile.email, 'password'); });
});
afterEach(() => { queries.clear(); });

test('clears the account immediately and never persists a refresh arriving after logout', async () => {
  const rotation = deferred<Tokens>();
  const started = deferred<void>();
  requestMock.mockImplementation(async <T,>(path: string, _options?: RequestInit, access?: string): Promise<T> => {
    if (path === '/auth/refresh/') { started.resolve(); return rotation.promise as Promise<T>; }
    if (path === '/private/' && access === initial.access) throw new ApiError('Expired', 401);
    return undefined as T;
  });
  const pending = session.api('/private/').catch(error => error);
  await started.promise;
  let logout!: Promise<void>;
  await act(async () => { logout = session.logout(); });
  expect(session.user).toBeNull();
  await act(async () => { rotation.resolve({ access: 'late-access', refresh: 'late-refresh' }); await pending; await logout; });
  expect(saveMock).not.toHaveBeenCalledWith('late-refresh');
  expect(saveMock).toHaveBeenLastCalledWith(null);
  expect(requestMock.mock.calls.filter(([path]) => path === '/auth/refresh/')).toHaveLength(1);
  expect(requestMock).toHaveBeenCalledWith('/auth/logout/', expect.objectContaining({ body: JSON.stringify({ refresh: 'late-refresh' }) }), 'late-access');
  await session.api('/public/');
  expect(requestMock).toHaveBeenLastCalledWith('/public/', {}, undefined);
});

test('an old refresh rejection cannot erase a newly connected account or SecureStore', async () => {
  const rotation = deferred<Tokens>();
  const started = deferred<void>();
  const bob = { ...profile, id: 'bob', email: 'bob@example.com' };
  requestMock.mockImplementation(async <T,>(path: string, _options?: RequestInit, access?: string): Promise<T> => {
    if (path === '/auth/refresh/') { started.resolve(); return rotation.promise as Promise<T>; }
    if (path === '/private/' && access === initial.access) throw new ApiError('Expired', 401);
    return (path === '/auth/login/' ? { access: 'bob-access', refresh: 'bob-refresh' } : bob) as T;
  });
  const pending = session.api('/private/').catch(error => error);
  await started.promise;
  await act(async () => { await session.login(bob.email, 'password'); });
  await act(async () => { rotation.reject(new ApiError('Revoked', 401)); await pending; });
  expect(session.user?.id).toBe('bob');
  expect(saveMock).toHaveBeenLastCalledWith('bob-refresh');
});

test('transient refresh failure preserves the account and allows retry', async () => {
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
  expect(saveMock).toHaveBeenLastCalledWith('refresh');
  offline = false;
  await expect(session.api('/private/')).resolves.toBe('ok');
  expect(saveMock).toHaveBeenLastCalledWith('new-refresh');
});
