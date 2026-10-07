import { useQueries } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import type { TicketEvent } from '../../packages/api-client/src';
import { useSession } from './session';
import { useSavedEvents } from './useSavedEvents';
import EventCard from './EventCard';
import { Alert, Empty, Loading } from './ui';
import { Icon } from './Icon';
import { Reveal } from './motion';

export default function Saved() {
  const { api, user } = useSession(); const { saved, toggle } = useSavedEvents();
  const results = useQueries({ queries: saved.map(id => ({ queryKey: ['saved-event', id, user?.id], queryFn: () => api<TicketEvent>(`/events/${id}/`), retry: false })) });
  return <><div className="page-heading"><p className="eyebrow"><Icon name="heart" size={15} />Made for your calendar</p><h1>Your shortlist.</h1><p className="muted">Keep a little inspiration for later. Saved on this browser, without needing an account.</p></div>
    {!saved.length && <Empty><Icon name="heart" size={36} /><h2>A good moment is worth saving.</h2><p>Tap the heart on an event to keep it here.</p><Link className="primary button" to="/">Explore events <Icon name="arrow" /></Link></Empty>}
    <div className="event-grid">{results.map((result, index) => result.data ? <Reveal key={saved[index]} delay={index % 3 * 70}><EventCard event={result.data} index={index} /></Reveal> : <div key={saved[index]} className="panel">{result.isPending ? <Loading /> : <><Alert error={result.error} /><button onClick={() => toggle(saved[index])}>Remove unavailable event</button></>}</div>)}</div></>;
}
