import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { AppState } from 'react-native';
import { useQueryClient } from '@tanstack/react-query';
import type { ApiRequest, Profile, Tokens } from '../../packages/api-client/src';
import { post } from '../../packages/api-client/src';
import { ApiError, apiBase, getRefresh, request, saveRefresh } from './api';

interface Session { user: Profile | null; ready: boolean; api: ApiRequest; login: (email: string, password: string, displayName?: string) => Promise<void>; logout: () => Promise<void>; updateProfile: (profile: Profile) => void; protectedSource: (path: string) => Promise<{ uri: string; headers: { Authorization: string } }> }
const Context = createContext<Session | null>(null);
export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Profile | null>(null); const [ready, setReady] = useState(false); const tokens = useRef<Tokens | null>(null); const refreshing = useRef<Promise<Tokens> | null>(null); const queries = useQueryClient();
  const refresh = useCallback(async () => {
    const stored = tokens.current?.refresh ?? await getRefresh(); if (!stored) throw new Error('Please sign in again.');
    if (!refreshing.current) refreshing.current = request<Tokens>('/auth/refresh/', post({ refresh: stored }));
    try { const next = await refreshing.current; tokens.current = next; await saveRefresh(next.refresh); return next; }
    finally { refreshing.current = null; }
  }, []);
  const api: ApiRequest = useCallback(async <T,>(path: string, options: RequestInit = {}) => {
    try { return await request<T>(path, options, tokens.current?.access); }
    catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401 || !tokens.current || path.startsWith('/auth/')) throw error;
      try { const next = await refresh(); return await request<T>(path, options, next.access); }
      catch (refreshError) { if (refreshError instanceof ApiError && refreshError.status === 401) { tokens.current = null; await saveRefresh(null); setUser(null); queries.clear(); } throw refreshError; }
    }
  }, [refresh, queries]);
  useEffect(() => {
    let active = true;
    async function restore() {
      try { if (await getRefresh()) { const next = await refresh(); const profile = await request<Profile>('/me/', {}, next.access); if (active) setUser(profile); } }
      catch (error) { if (error instanceof ApiError && error.status === 401) { tokens.current = null; await saveRefresh(null); } }
      finally { if (active) setReady(true); }
    }
    void restore();
    const subscription = AppState.addEventListener('change', state => { if (state === 'active') void queries.invalidateQueries(); });
    return () => { active = false; subscription.remove(); };
  }, [queries, refresh]);
  async function login(email: string, password: string, displayName?: string) {
    const next = await request<Tokens>(displayName === undefined ? '/auth/login/' : '/auth/register/', post({ email, password, display_name: displayName }));
    const profile = await request<Profile>('/me/', {}, next.access); tokens.current = next; await saveRefresh(next.refresh); setUser(profile);
  }
  async function logout() { try { const next = await refresh(); await request('/auth/logout/', post({ refresh: next.refresh }), next.access); } finally { tokens.current = null; await saveRefresh(null); setUser(null); queries.clear(); } }
  const protectedSource = useCallback(async (path: string) => { await api('/me/'); if (!tokens.current) throw new Error('Sign in to view this ticket.'); return { uri: `${apiBase}${path}`, headers: { Authorization: `Bearer ${tokens.current.access}` } }; }, [api]);
  return <Context.Provider value={{ user, ready, api, login, logout, updateProfile: setUser, protectedSource }}>{children}</Context.Provider>;
}
export function useSession() { const value = useContext(Context); if (!value) throw new Error('Session provider missing'); return value; }
