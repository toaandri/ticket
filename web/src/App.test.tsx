import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';

const fetchMock = vi.fn();
function json(data: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } }));
}
beforeEach(() => { vi.stubGlobal('fetch', fetchMock); fetchMock.mockReset(); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('Account workspace', () => {
  it('signs in and loads only the organizations returned by the API', async () => {
    fetchMock.mockImplementationOnce(() => json({ access: 'access', refresh: 'refresh' }))
      .mockImplementationOnce(() => json({ id: 'user-1', email: 'alice@example.com', display_name: 'Alice' }))
      .mockImplementationOnce(() => json({ results: [{ id: 'org-1', name: 'Concert team', slug: 'concert-team', owner: 'user-1' }] }));
    const user = userEvent.setup(); render(<App />);
    await user.type(screen.getByLabelText('Email'), 'alice@example.com');
    await user.type(screen.getByLabelText('Password'), 'example-password-93!');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByText('Concert team')).toBeInTheDocument();
    expect(screen.getByText('Hello, Alice.')).toBeInTheDocument();
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe('Bearer access');
    expect(localStorage.length).toBe(0);
  });

  it('shows API errors and leaves the sign-in form available', async () => {
    fetchMock.mockImplementationOnce(() => json({ message: 'Invalid credentials.' }, 401));
    const user = userEvent.setup(); render(<App />);
    await user.type(screen.getByLabelText('Email'), 'alice@example.com');
    await user.type(screen.getByLabelText('Password'), 'wrong');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid credentials.');
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeEnabled();
  });

  it('supports registration without persisting credentials in browser storage', async () => {
    const user = userEvent.setup(); render(<App />);
    await user.click(screen.getByRole('button', { name: 'New here? Create an account' }));
    expect(screen.getByLabelText('Display name')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toHaveAttribute('autocomplete', 'new-password');
    expect(sessionStorage.length).toBe(0);
  });
});
