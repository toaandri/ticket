import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import type { Paginated, TicketEvent } from '../../packages/api-client/src';
import { money } from '../../packages/api-client/src';
import { useSession } from './session';
import { Alert, Empty, Loading, humanDate } from './ui';

export default function Discover() {
  const { api } = useSession();
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [page, setPage] = useState(1);
  const [city, setCity] = useState('');
  const params = new URLSearchParams({ search, category, city, page: String(page) });
  const events = useQuery({ queryKey: ['events', params.toString()], queryFn: () => api<Paginated<TicketEvent>>(`/events/?${params}`) });
  return <>
    <section className="hero"><div><p className="eyebrow">Good moments start here</p><h1>Make room<br />for something <em>great.</em></h1><p>Small stages. Big ideas. Your next memorable night is closer than you think.</p><a className="primary button" href="#events">Explore events <span aria-hidden="true">↗</span></a><p className="demo-note">Portfolio demo · Synthetic events · Simulated payments</p></div><div className="hero-art" aria-hidden="true"><div className="art-orbit" /><div className="art-ticket"><span>ADMIT ONE</span><strong>Be there.</strong><div className="art-barcode" /><span>A moment worth making</span></div><span className="art-sticker">Find your<br />people.</span></div></section>
    <section id="events"><div className="section-heading"><div><p className="eyebrow">The calendar is calling</p><h2>Find your next event</h2></div><span className="muted">{events.data?.count ?? '…'} events to explore</span></div>
      <form className="filters" onSubmit={event => event.preventDefault()}><label className="search-label">Search events<input type="search" placeholder="Music, theatre, a new idea…" value={search} onChange={event => { setSearch(event.target.value); setPage(1); }} /></label><label>City<input value={city} placeholder="Anywhere" onChange={event => { setCity(event.target.value); setPage(1); }} /></label><label>Category<select value={category} onChange={event => { setCategory(event.target.value); setPage(1); }}><option value="">All categories</option>{['Music', 'Theatre', 'Technology'].map(value => <option key={value}>{value}</option>)}</select></label></form>
      {events.isPending ? <Loading /> : <Alert error={events.error} />}
      {events.data && !events.data.results.length && <Empty><h3>No events found</h3><p>Try another search or category.</p></Empty>}
      <div className="event-grid">{events.data?.results.map((event, index) => <Link key={event.id} to={`/events/${event.id}`} className="event-card"><div className={`event-art art-${event.category?.toLowerCase() ?? 'music'}`}><span className="pill">{event.category}</span><span className="event-art-number" aria-hidden="true">{String(index + 1).padStart(2, '0')}</span><strong aria-hidden="true">{event.category === 'Theatre' ? 'On stage.' : event.category === 'Technology' ? 'What’s next?' : 'Feel it.'}</strong></div><div className="event-card-copy"><p className="event-date">{humanDate(event.start_at, event.event_timezone)}</p><h3>{event.title}</h3><p className="muted">{event.venue_name} · {event.city}</p><div className="card-bottom"><span>{event.ticket_types.length ? `From ${money(Math.min(...event.ticket_types.map(type => type.price_minor)), event.ticket_types[0].currency)}` : 'Details coming soon'}</span><span className="pill subtle">{event.status === 'PUBLISHED' ? 'See tickets ↗' : event.status}</span></div></div></Link>)}</div>
      {events.data && (events.data.next || events.data.previous) && <div className="pagination"><button disabled={!events.data.previous} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page}</span><button disabled={!events.data.next} onClick={() => setPage(page + 1)}>Next</button></div>}
    </section><section className="organize-banner"><div><p className="eyebrow">Bring people together</p><h2>Your event. A little more effortless.</h2><p>Build your team, set the stage and keep everyone moving.</p></div><Link className="primary button" to="/workspace">Open your workspace ↗</Link></section>
  </>;
}
