import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { AppState } from 'react-native';
import { useQueryClient } from '@tanstack/react-query';
import type { ApiRequest, Profile, Tokens } from '../../packages/api-client/src';
import { post } from '../../packages/api-client/src';
import { ApiError, apiBase, getRefresh, request, saveRefresh } from './api';
import { SessionCredentials } from '../../packages/api-client/src/session';

interface Session { user: Profile | null; ready: boolean; api: ApiRequest; login: (email: string, password: string, displayName?: string) => Promise<void>; logout: () => Promise<void>; updateProfile: (profile: Profile) => void; protectedSource: (path: string) => Promise<{ uri: string; headers: { Authorization: string } }> }
const Context = createContext<Session | null>(null);
export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Profile | null>(null); const [ready, setReady] = useState(false);
  const [credentials] = useState(() => new SessionCredentials(getRefresh, saveRefresh));
  const queries = useQueryClient();
  const refresh = useCallback((version = credentials.version) => credentials.rotate(
    stored => request<Tokens>('/auth/refresh/', post({ refresh: stored })), version,
  ), [credentials]);
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
      try { next = credentials.tokens !== sent && credentials.tokens ? credentials.tokens : await refresh(version); }
      catch (refreshError) {
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
  }, [credentials, refresh, queries]);
  useEffect(() => {
    let active = true;
    const version = credentials.version;
    async function restore() {
      try {
        if (await getRefresh()) {
          credentials.assertCurrent(version);
          const next = await refresh(version);
          credentials.assertCurrent(version);
          const profile = await request<Profile>('/me/', {}, next.access);
          if (active && credentials.version === version) setUser(profile);
        }
      }
      catch (error) {
        if (credentials.version === version && error instanceof ApiError && error.status === 401) {
          setUser(null); queries.clear(); await credentials.clear();
        }
      }
      finally { if (active) setReady(true); }
    }
    void restore();
    const subscription = AppState.addEventListener('change', state => { if (state === 'active') void queries.invalidateQueries(); });
    return () => { active = false; subscription.remove(); };
  }, [credentials, queries, refresh]);
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
    const revocation = credentials.tokens ? refresh() : null;
    const clearing = credentials.clear();
    setUser(null); queries.clear();
    try { if (revocation) { const next = await revocation; await request('/auth/logout/', post({ refresh: next.refresh }), next.access); } }
    finally { await clearing; }
  }
  const protectedSource = useCallback(async (path: string) => { await api('/me/'); if (!credentials.tokens) throw new Error('Sign in to view this ticket.'); return { uri: `${apiBase}${path}`, headers: { Authorization: `Bearer ${credentials.tokens.access}` } }; }, [api, credentials]);
  return <Context.Provider value={{ user, ready, api, login, logout, updateProfile: setUser, protectedSource }}>{children}</Context.Provider>;
}
export function useSession() { const value = useContext(Context); if (!value) throw new Error('Session provider missing'); return value; }
