import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

export interface User { id: string; email: string; display_name: string }
export interface Organization { id: string; name: string; slug: string }
export interface Tokens { access: string; refresh: string }
const base = (process.env.EXPO_PUBLIC_API_BASE_URL ?? (Platform.OS === 'android' ? 'http://10.0.2.2:8000/api/v1' : 'http://localhost:8000/api/v1')).replace(/\/$/, '');
const refreshKey = 'ticket.refresh';
let browserRefresh: string | null = null;

export async function saveRefresh(value: string | null) {
  if (Platform.OS === 'web') { browserRefresh = value; return; }
  if (value) await SecureStore.setItemAsync(refreshKey, value);
  else await SecureStore.deleteItemAsync(refreshKey);
}
export async function getRefresh() {
  return Platform.OS === 'web' ? browserRefresh : SecureStore.getItemAsync(refreshKey);
}
export async function request<T>(path: string, options: RequestInit = {}, access?: string): Promise<T> {
  const response = await fetch(`${base}${path}`, { ...options,
    headers: { 'Content-Type': 'application/json', ...(access ? { Authorization: `Bearer ${access}` } : {}), ...options.headers } });
  if (!response.ok) {
    const data = await response.json().catch(() => null) as { message?: string; details?: Record<string, unknown> } | null;
    throw new Error(data?.details ? Object.values(data.details).flat().join(' ') : data?.message ?? `Request failed (${response.status}).`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
