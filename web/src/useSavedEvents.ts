import { useEffect, useState } from 'react';

const key = 'ticket.saved-events';
function read(): string[] {
  try { const value: unknown = JSON.parse(localStorage.getItem(key) ?? '[]'); return Array.isArray(value) ? [...new Set(value.filter((id): id is string => typeof id === 'string' && /^[a-f0-9-]{36}$/i.test(id)))].slice(0, 100) : []; }
  catch { return []; }
}
export function useSavedEvents() {
  const [saved, setSaved] = useState(read);
  useEffect(() => { const sync = () => setSaved(read()); window.addEventListener('storage', sync); window.addEventListener('ticket:saved', sync); return () => { window.removeEventListener('storage', sync); window.removeEventListener('ticket:saved', sync); }; }, []);
  function toggle(id: string) {
    let current = saved;
    try { if (localStorage.getItem(key) !== null) current = read(); } catch { /* Use the in-memory shortlist. */ }
    const next = current.includes(id) ? current.filter(value => value !== id) : [...current, id].slice(-100);
    try { localStorage.setItem(key, JSON.stringify(next)); window.dispatchEvent(new Event('ticket:saved')); } catch { /* Keep the current view usable when browser storage is unavailable. */ }
    setSaved(next);
  }
  return { saved, toggle };
}
