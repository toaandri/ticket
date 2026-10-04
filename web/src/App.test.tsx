import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';
const fetchMock = vi.fn();
const profile = { id: 'user-1', email: 'alice@example.com', display_name: 'Alice', email_verified_at: '2026-01-01T00:00:00Z' };
const page = { count: 0, results: [], next: null, previous: null };
function json(data: unknown, status = 200) { return Promise.resolve(new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })); }
beforeEach(() => { window.history.replaceState({}, '', '/account'); vi.stubGlobal('fetch', fetchMock); fetchMock.mockReset(); fetchMock.mockImplementation((url: string) => json(url.endsWith('/me/') ? profile : url.endsWith('/auth/login/') ? { access: 'access', refresh: 'refresh' } : page)); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
describe('Account and discovery', () => {
  it('signs in, authorizes wallet requests, and keeps credentials out of browser storage', async () => { const user = userEvent.setup(); render(<App />); await user.type(screen.getByLabelText('Email'), profile.email); await user.type(screen.getByLabelText('Password'), 'example-password-93!'); await user.click(screen.getByRole('button', { name: 'Sign in' })); expect(await screen.findByText('Hello, Alice.')).toBeInTheDocument(); expect(await screen.findByText('Your next event is waiting.')).toBeInTheDocument(); const call = fetchMock.mock.calls.find(([url]) => url.includes('/tickets/')); expect(call?.[1].headers.Authorization).toBe('Bearer access'); expect(localStorage.length + sessionStorage.length).toBe(0); });
  it('shows an authentication rejection and permits retry', async () => { fetchMock.mockImplementation(() => json({ message: 'Invalid credentials.' }, 401)); const user = userEvent.setup(); render(<App />); await user.type(screen.getByLabelText('Email'), profile.email); await user.type(screen.getByLabelText('Password'), 'wrong'); await user.click(screen.getByRole('button', { name: 'Sign in' })); expect(await screen.findByRole('alert')).toHaveTextContent('Invalid credentials.'); expect(screen.getByRole('button', { name: 'Sign in' })).toBeEnabled(); expect(screen.queryByText('My tickets', { selector: 'h2' })).not.toBeInTheDocument(); });
  it('exposes registration and public search without authentication', async () => { const user = userEvent.setup(); render(<App />); await user.click(screen.getByRole('button', { name: 'New here? Create an account' })); expect(screen.getByLabelText('Display name')).toBeInTheDocument(); await user.click(screen.getByRole('link', { name: 'Discover' })); expect(await screen.findByText('No events found')).toBeInTheDocument(); await user.type(screen.getByLabelText('Search events'), 'jazz'); expect(fetchMock.mock.calls.some(([url]) => url.includes('search=jazz'))).toBe(true); });
});
