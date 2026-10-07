import { Link } from 'react-router-dom';
import type { TicketEvent } from '../../packages/api-client/src';
import { money } from '../../packages/api-client/src';
import { Icon } from './Icon';
import { humanDate } from './ui';
import { useSavedEvents } from './useSavedEvents';

export default function EventCard({ event, index = 0 }: { event: TicketEvent; index?: number }) {
  const { saved, toggle } = useSavedEvents(); const isSaved = saved.includes(event.id); const date = new Date(event.start_at);
  return <article className="event-card"><Link to={`/events/${event.id}`} className={`event-art art-${event.category?.toLowerCase() ?? 'music'}`} aria-label={`View ${event.title}`}>
    <span className="pill">{event.category || 'Experience'}</span><span className="event-art-number" aria-hidden="true">{String(index + 1).padStart(2, '0')} / TICKET</span><span className="poster-shape poster-shape-one" /><span className="poster-shape poster-shape-two" />
    <strong aria-hidden="true">{event.category === 'Theatre' ? <>Take<br />the stage.</> : event.category === 'Technology' ? <>Ideas.<br />In motion.</> : <>Feel<br />everything.</>}</strong>
    <div className="event-stamp" aria-hidden="true"><span>{new Intl.DateTimeFormat('en', { month: 'short', timeZone: event.event_timezone }).format(date)}</span><b>{new Intl.DateTimeFormat('en', { day: '2-digit', timeZone: event.event_timezone }).format(date)}</b></div></Link>
    <button className={`save-event ${isSaved ? 'is-saved' : ''}`} aria-label={`${isSaved ? 'Unsave' : 'Save'} ${event.title}`} aria-pressed={isSaved} onClick={() => toggle(event.id)}><Icon name="heart" size={18} /></button>
    <div className="event-card-copy"><p className="event-date"><Icon name="calendar" size={14} />{humanDate(event.start_at, event.event_timezone)}</p><h3><Link to={`/events/${event.id}`}>{event.title}</Link></h3><p className="event-location"><Icon name="pin" size={15} />{event.venue_name || 'Online'} · {event.city || 'Anywhere'}</p>
      <div className="card-bottom"><span>{event.ticket_types.length ? <><small>From</small> {money(Math.min(...event.ticket_types.map(type => type.price_minor)), event.ticket_types[0].currency)}</> : 'Details coming soon'}</span><Link to={`/events/${event.id}`} className="card-cta" aria-label={`Tickets for ${event.title}`}>{event.status === 'PUBLISHED' ? 'See tickets' : event.status}<Icon name="arrowUp" size={16} /></Link></div></div>
  </article>;
}
