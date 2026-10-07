import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';
import { useSavedEvents } from './useSavedEvents';

beforeEach(() => { localStorage.clear(); sessionStorage.clear(); window.history.replaceState({}, '', '/'); vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ count: 0, results: [], next: null, previous: null }), { headers: { 'Content-Type': 'application/json' } }))); });
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); });

describe('Interface preferences and navigation', () => {
  it('switches theme and lets visitors pause decorative motion', async () => {
    const user = userEvent.setup(); render(<App />);
    await user.click(screen.getByRole('button', { name: 'Switch to dark theme' }));
    expect(document.documentElement.dataset.theme).toBe('dark'); expect(localStorage.getItem('ticket.theme')).toBe('dark');
    await user.click(screen.getByRole('button', { name: 'Pause animations' }));
    expect(document.documentElement.dataset.motion).toBe('off'); expect(screen.getByRole('button', { name: 'Resume animations' })).toHaveAttribute('aria-pressed', 'true');
  });
  it('opens keyboard quick search, focuses the input and closes on navigation', async () => {
    const user = userEvent.setup(); render(<App />); fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    expect(screen.getByRole('dialog')).toBeInTheDocument(); expect(screen.getByLabelText('Quick search events')).toHaveFocus();
    await user.click(screen.getByRole('link', { name: /Saved events.*Your personal shortlist/ }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument(); expect(screen.getByRole('heading', { name: 'Your shortlist.' })).toBeInTheDocument();
  });
  it('keeps filters in the URL and switches to list presentation', async () => {
    const user = userEvent.setup(); render(<App />); await user.click(screen.getByRole('button', { name: 'Technology' }));
    expect(new URLSearchParams(location.search).get('category')).toBe('Technology');
    await user.click(screen.getByRole('button', { name: 'List view' })); expect(screen.getByRole('button', { name: 'List view' })).toHaveAttribute('aria-pressed', 'true');
    await user.click(screen.getByRole('button', { name: 'Clear filters' })); await waitFor(() => expect(location.search).toBe(''));
  });
});

function Shortlist() { const { saved, toggle } = useSavedEvents(); return <><output aria-label="Saved count">{saved.length}</output><button onClick={() => toggle('12345678-1234-1234-1234-123456789abc')}>Toggle event</button></>; }
describe('Saved events', () => {
  it('ignores corrupt storage and synchronizes independent cards', () => {
    localStorage.setItem('ticket.saved-events', '{broken'); render(<><Shortlist /><Shortlist /></>);
    fireEvent.click(screen.getAllByRole('button')[0]); expect(screen.getAllByLabelText('Saved count').every(item => item.textContent === '1')).toBe(true);
    fireEvent.click(screen.getAllByRole('button')[1]); expect(JSON.parse(localStorage.getItem('ticket.saved-events')!)).toEqual([]);
  });
  it('still adds and removes a saved event when storage is blocked', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('Blocked'); }); vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Blocked'); });
    render(<Shortlist />); fireEvent.click(screen.getByRole('button')); expect(screen.getByLabelText('Saved count')).toHaveTextContent('1'); fireEvent.click(screen.getByRole('button')); expect(screen.getByLabelText('Saved count')).toHaveTextContent('0');
  });
});
