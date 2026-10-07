import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import type { Paginated, TicketEvent } from '../../packages/api-client/src';
import { useSession } from './session';
import { Alert, Loading } from './ui';
import { Icon, type IconName } from './Icon';

const shortcuts: { path: string; title: string; detail: string; icon: IconName }[] = [
  { path: '/', title: 'Discover events', detail: 'Find your next good moment', icon: 'compass' },
  { path: '/saved', title: 'Saved events', detail: 'Your personal shortlist', icon: 'heart' },
  { path: '/account', title: 'My tickets', detail: 'Your wallet and account', icon: 'ticket' },
  { path: '/workspace', title: 'Your workspace', detail: 'Events, teams and reports', icon: 'grid' },
  { path: '/gate', title: 'Gate scanner', detail: 'Verify an admission online', icon: 'scan' },
];
export default function SearchDialog() {
  const dialog = useRef<HTMLDialogElement>(null); const input = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false); const [search, setSearch] = useState(''); const { api, user } = useSession();
  const show = useCallback(() => { dialog.current?.showModal(); setOpen(true); input.current?.focus(); }, []);
  const close = () => { dialog.current?.close(); setOpen(false); };
  useEffect(() => {
    const listener = (event: KeyboardEvent) => { if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); show(); } };
    document.addEventListener('keydown', listener); return () => document.removeEventListener('keydown', listener);
  }, [show]);
  const results = useQuery({ queryKey: ['quick-search', search.trim(), user?.id], queryFn: () => api<Paginated<TicketEvent>>(`/events/?${new URLSearchParams({ search: search.trim() })}`), enabled: open && search.trim().length >= 2 });
  return <><button className="search-trigger" aria-label="Search events and pages" onClick={show}><Icon name="search" /><span>Quick search</span><kbd>Ctrl K</kbd></button>
    <dialog ref={dialog} className="search-dialog" aria-labelledby="search-title" onClose={() => setOpen(false)} onClick={event => { if (event.target === event.currentTarget) close(); }}>
      <div className="search-dialog-content"><div className="dialog-heading"><h2 id="search-title">Where to next?</h2><button className="icon-button" aria-label="Close search" onClick={close}><Icon name="close" /></button></div>
        <label className="command-input"><Icon name="search" /><span className="sr-only">Quick search events</span><input ref={input} type="search" placeholder="Search an event, or jump to a page…" value={search} onChange={event => setSearch(event.target.value)} /></label>
        {search.trim().length >= 2 ? <div className="command-results" aria-live="polite">{results.isPending && <Loading />}<Alert error={results.error} />{results.data?.results.slice(0, 6).map(event => <Link key={event.id} to={`/events/${event.id}`} onClick={close}><Icon name="calendar" /><div><strong>{event.title}</strong><span>{event.category} · {event.city}</span></div><Icon name="arrowUp" /></Link>)}{results.data && !results.data.results.length && <p className="muted">No matching events. Try another name.</p>}</div> : <div className="command-results">{shortcuts.map(shortcut => <Link key={shortcut.path} to={shortcut.path} onClick={close}><Icon name={shortcut.icon} /><div><strong>{shortcut.title}</strong><span>{shortcut.detail}</span></div><Icon name="chevron" /></Link>)}</div>}
        <p className="command-foot"><kbd>Tab</kbd> to explore <span>·</span> <kbd>Esc</kbd> to close</p></div>
    </dialog></>;
}
