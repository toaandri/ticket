import type { components } from '../generated/types';
export type { components, paths } from '../generated/types';
export type TicketEvent = components['schemas']['Event'];
export type TicketType = components['schemas']['TicketType'];
export type Availability = components['schemas']['Availability'];
export type Reservation = components['schemas']['Reservation'];
export type Order = components['schemas']['Order'];
export type Payment = components['schemas']['Payment'];
export type TicketReport = components['schemas']['TicketReport'];
export type Ticket = components['schemas']['Ticket'];
export type Organization = components['schemas']['Organization'];
export type Venue = components['schemas']['Venue'];
export type Member = components['schemas']['Member'];
export type Metrics = components['schemas']['EventMetrics'];
export type Notification = components['schemas']['Notification'];
export type CheckIn = components['schemas']['CheckIn'];
export type Profile = components['schemas']['Profile'];
export type Promotion = components['schemas']['Promotion'];
export type Audit = components['schemas']['Audit'];
export type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };
export interface Tokens { access: string; refresh: string }
export type ApiRequest = <T>(path: string, options?: RequestInit) => Promise<T>;

export function money(minor: number, currency = 'EUR') {
  const exponent = 2;
  return new Intl.NumberFormat('en', { style: 'currency', currency, maximumFractionDigits: exponent }).format(minor / 10 ** exponent);
}
export function remainingSeconds(expiresAt: string, now = Date.now()) {
  return Math.max(0, Math.ceil((Date.parse(expiresAt) - now) / 1000));
}
export function newKey() {
  // Modern browsers and Expo provide crypto.randomUUID. Native callers can also
  // pass a device UUID generated through expo-crypto when needed.
  return globalThis.crypto.randomUUID();
}
export function post(body: unknown, key?: string): RequestInit {
  return { method: 'POST', body: JSON.stringify(body), headers: key ? { 'Idempotency-Key': key } : undefined };
}
