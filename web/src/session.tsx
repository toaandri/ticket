import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { ApiRequest, Profile, Tokens } from '../../packages/api-client/src';
import { post } from '../../packages/api-client/src';
import { ApiError, request } from './api';

interface Session { user: Profile | null; api: ApiRequest; login: (email: string, password: string, displayName?: string) => Promise<void>; logout: () => Promise<void>; updateProfile: (user: Profile) => void }
const Context = createContext<Session | null>(null);
export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Profile | null>(null);
  const tokens = useRef<Tokens | null>(null);
  const refreshing = useRef<Promise<Tokens> | null>(null);
  const queries = useQueryClient();
  const api: ApiRequest = useCallback(async <T,>(path: string, options: RequestInit = {}) => {
    try { return await request<T>(path, options, tokens.current?.access); }
    catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401 || !tokens.current || path.startsWith('/auth/')) throw error;
      if (!refreshing.current) refreshing.current = request<Tokens>('/auth/refresh/', post({ refresh: tokens.current.refresh }));
      try { tokens.current = await refreshing.current; }
      catch (refreshError) { tokens.current = null; setUser(null); queries.clear(); throw refreshError; }
      finally { refreshing.current = null; }
      return request<T>(path, options, tokens.current.access);
    }
  }, [queries]);
  async function login(email: string, password: string, displayName?: string) {
    tokens.current = await request<Tokens>(displayName === undefined ? '/auth/login/' : '/auth/register/', post({ email, password, display_name: displayName }));
    setUser(await request<Profile>('/me/', {}, tokens.current.access));
  }
  async function logout() {
    try { if (tokens.current) { tokens.current = await request<Tokens>('/auth/refresh/', post({ refresh: tokens.current.refresh })); await request('/auth/logout/', post({ refresh: tokens.current.refresh }), tokens.current.access); } }
    finally { tokens.current = null; setUser(null); queries.clear(); }
  }
  return <Context.Provider value={{ user, api, login, logout, updateProfile: setUser }}>{children}</Context.Provider>;
}
export function useSession() { const session = useContext(Context); if (!session) throw new Error('Session provider missing'); return session; }
