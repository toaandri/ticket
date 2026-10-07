import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { ApiRequest, Profile, Tokens } from '../../packages/api-client/src';
import { post } from '../../packages/api-client/src';
import { ApiError, request } from './api';
import { SessionCredentials } from '../../packages/api-client/src/session';

interface Session { user: Profile | null; api: ApiRequest; login: (email: string, password: string, displayName?: string) => Promise<void>; logout: () => Promise<void>; updateProfile: (user: Profile) => void }
const Context = createContext<Session | null>(null);
export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Profile | null>(null);
  const [credentials] = useState(() => new SessionCredentials());
  const queries = useQueryClient();
  const api: ApiRequest = useCallback(async <T,>(path: string, options: RequestInit = {}) => {
    const version = credentials.version;
    const sent = credentials.tokens;
    try {
      const result = await request<T>(path, options, sent?.access);
      credentials.assertCurrent(version);
      return result;
    }
    catch (error) {
      credentials.assertCurrent(version);
      if (!(error instanceof ApiError) || error.status !== 401 || !sent || path.startsWith('/auth/')) throw error;
      let next: Tokens;
      try {
        next = credentials.tokens !== sent && credentials.tokens ? credentials.tokens :
          await credentials.rotate(refresh => request<Tokens>('/auth/refresh/', post({ refresh })), version);
      } catch (refreshError) {
        if (credentials.version === version && refreshError instanceof ApiError && refreshError.status === 401) {
          setUser(null); queries.clear(); await credentials.clear();
        }
        throw refreshError;
      }
      credentials.assertCurrent(version);
      const result = await request<T>(path, options, next.access);
      credentials.assertCurrent(version);
      return result;
    }
  }, [credentials, queries]);
  async function login(email: string, password: string, displayName?: string) {
    const clearing = credentials.clear();
    const version = credentials.version;
    setUser(null); queries.clear(); await clearing;
    credentials.assertCurrent(version);
    const next = await request<Tokens>(displayName === undefined ? '/auth/login/' : '/auth/register/', post({ email, password, display_name: displayName }));
    credentials.assertCurrent(version);
    const profile = await request<Profile>('/me/', {}, next.access);
    await credentials.set(next, version);
    setUser(profile);
  }
  async function logout() {
    const revocation = credentials.tokens ? credentials.rotate(refresh => request<Tokens>('/auth/refresh/', post({ refresh }))) : null;
    const clearing = credentials.clear();
    setUser(null); queries.clear();
    try { if (revocation) { const next = await revocation; await request('/auth/logout/', post({ refresh: next.refresh }), next.access); } }
    finally { await clearing; }
  }
  return <Context.Provider value={{ user, api, login, logout, updateProfile: setUser }}>{children}</Context.Provider>;
}
export function useSession() { const session = useContext(Context); if (!session) throw new Error('Session provider missing'); return session; }
