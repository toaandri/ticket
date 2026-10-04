import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { Availability, Order, Payment, Reservation, TicketEvent } from '../../packages/api-client/src';
import { money, newKey, post, remainingSeconds } from '../../packages/api-client/src';
import { useSession } from './session';
import { Alert, Countdown, Field, Form, Loading, humanDate } from './ui';

export default function EventPage() {
  const { id } = useParams(); const { user, api } = useSession(); const queries = useQueryClient();
  const event = useQuery({ queryKey: ['event', id], queryFn: () => api<TicketEvent>(`/events/${id}/`) });
  const availability = useQuery({ queryKey: ['availability', id], queryFn: () => api<Availability>(`/events/${id}/availability/`), refetchInterval: 10000 });
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [seats, setSeats] = useState<string[]>([]); const [hold, setHold] = useState<Reservation | null>(null);
  const [order, setOrder] = useState<Order | null>(null); const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  const [provider, setProvider] = useState('MOCK'); const [scenario, setScenario] = useState('success');
  const lastRequest = useRef<{ payload: string; key: string } | null>(null);
  const paymentKey = useRef(newKey());
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  useEffect(() => {
    let active = true; let socket: WebSocket | undefined; let retry: ReturnType<typeof setTimeout>;
    const refresh = () => { void queries.invalidateQueries({ queryKey: ['availability', id] }); };
    function connect() {
      if (!active || typeof WebSocket === 'undefined') return;
      const url = new URL(`/ws/events/${id}/availability/`, window.location.href); url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      socket = new WebSocket(url);
      socket.onopen = refresh; socket.onmessage = refresh;
      socket.onclose = () => { if (active) retry = setTimeout(connect, 5000); };
    }
    connect(); return () => { active = false; clearTimeout(retry); socket?.close(); };
  }, [id, queries]);
  async function selectTickets() {
    setBusy(true); setError(null);
    try {
      const items = (event.data?.ticket_types ?? []).flatMap(type => type.kind === 'GENERAL' ? quantities[type.id] ? [{ ticket_type_id: type.id, quantity: quantities[type.id] }] : [] : seats.filter(seatId => availability.data?.seats.find(seat => seat.id === seatId)?.section_id === type.section_id).map(event_seat_id => ({ ticket_type_id: type.id, event_seat_id, quantity: 1 })));
      if (!items.length) throw new Error('Select at least one ticket or seat.');
      const payload = JSON.stringify({ event_id: id, items });
      if (lastRequest.current?.payload !== payload) lastRequest.current = { payload, key: newKey() };
      const result = await api<Reservation>('/reservations/', post(JSON.parse(payload), lastRequest.current.key));
      setHold(result); setOrder(null); paymentKey.current = newKey();
      await queries.invalidateQueries({ queryKey: ['availability', id] });
    } catch (err) { setError(err); } finally { setBusy(false); }
  }
  async function checkout(data: FormData) {
    if (!hold) return; setBusy(true); setError(null);
    try {
      const payload = { reservation_id: hold.id, promotion_code: String(data.get('promotion_code') ?? '') };
      setOrder(await api<Order>('/orders/', post(payload, `checkout:${hold.id}:${String(data.get('promotion_code') ?? '')}`)));
    } catch (err) { setError(err); } finally { setBusy(false); }
  }
  async function pay() {
    if (!order) return; setBusy(true); setError(null);
    try {
      const payment = await api<Payment>(`/orders/${order.id}/payments/`, post({ provider, scenario }, paymentKey.current));
      if (payment.checkout_url) window.location.assign(payment.checkout_url);
      setOrder(await api<Order>(`/orders/${order.id}/`));
      await queries.invalidateQueries();
    } catch (err) { setError(err); } finally { setBusy(false); }
  }
  async function cancel() {
    if (!hold) return; setBusy(true);
    try { await api(`/reservations/${hold.id}/cancel/`, post({})); setHold(null); setOrder(null); lastRequest.current = null; setSeats([]); await queries.invalidateQueries({ queryKey: ['availability', id] }); }
    catch (err) { setError(err); } finally { setBusy(false); }
  }
  if (event.isPending) return <Loading />;
  if (!event.data) return <Alert error={event.error} />;
  const detail = event.data;
  return <><Link className="back-link" to="/">← All events</Link><section className="event-detail-hero"><p className="eyebrow">{detail.category} · {detail.city}</p><h1>{detail.title}</h1><p>{humanDate(detail.start_at, detail.event_timezone)} · {detail.venue_name}</p><span className="pill">{detail.status}</span></section><div className="detail-grid"><section><h2>A little about the event</h2><p className="description">{detail.description}</p><div className="info-box"><h3>The details</h3><p>{detail.venue_name} · {detail.city}</p><p>{detail.age_policy}</p><p>{detail.cancellation_policy}</p></div></section><section className="panel"><h2>Choose your tickets</h2><Alert error={error ?? availability.error} />
    {order?.status === 'PAID' ? <div className="notice"><h3>You’re going!</h3><p>Your payment is simulated. Your tickets are ready in your wallet.</p><Link className="primary button" to="/account">View my tickets</Link></div> : order?.status === 'FAILED' ? <div className="alert"><h3>Payment declined</h3><p>No tickets were issued. Select tickets again to retry.</p><button onClick={() => { setOrder(null); setHold(null); lastRequest.current = null; }}>Choose again</button></div> : hold ? <><Countdown expiresAt={hold.expires_at} /><ul className="summary-list">{hold.items.map(item => <li key={item.id}>{item.quantity} × {item.name}<strong>{money(item.quantity * item.unit_price_minor, item.currency)}</strong></li>)}</ul>{!order ? <Form title="Continue to checkout" onSubmit={checkout} busy={busy}><Field label="Promotion code" name="promotion_code" required={false} /></Form> : <><dl className="price-breakdown"><dt>Subtotal</dt><dd>{money(order.subtotal_minor, order.currency)}</dd><dt>Discount</dt><dd>−{money(order.discount_minor ?? 0, order.currency)}</dd><dt>Total</dt><dd><strong>{money(order.total_minor, order.currency)}</strong></dd></dl><p className="demo-note">Test transactions only. No real money is charged.</p><label>Payment method<select value={provider} onChange={e => setProvider(e.target.value)}><option value="MOCK">Simulated payment</option><option value="STRIPE_TEST">Stripe test checkout (if enabled)</option></select></label>{provider === 'MOCK' && <label>Demo scenario<select value={scenario} onChange={e => { setScenario(e.target.value); paymentKey.current = newKey(); }}><option value="success">Successful payment</option><option value="decline">Declined payment</option><option value="pending">Pending payment</option><option value="delayed">Delayed payment</option><option value="timeout">Timeout</option></select></label>}{order.status === 'PAYMENT_PROCESSING' ? <div className="notice"><p>Payment pending. Your original hold deadline still applies.</p><button onClick={() => void api<Order>(`/orders/${order.id}/`).then(setOrder).catch(setError)}>Check payment status</button>{order.payments.find(payment => payment.provider === 'MOCK' && payment.status === 'PENDING') && <button onClick={() => void api(`/orders/${order.id}/simulate-payment/`, post({ payment_id: order.payments.find(payment => payment.status === 'PENDING')?.id, outcome: 'SUCCEEDED' }, newKey())).then(() => api<Order>(`/orders/${order.id}/`)).then(setOrder).catch(setError)}>Complete demo payment</button>}</div> : <button className="primary full" disabled={busy || remainingSeconds(hold.expires_at, now) === 0} onClick={() => void pay()}>Pay {money(order.total_minor, order.currency)} in test mode</button>}</>}<button className="quiet full" disabled={busy} onClick={() => void cancel()}>Release tickets and start again</button></> : <><p className="muted">Select general admission or your exact seats. Tickets are held for 10 minutes.</p>{detail.ticket_types.map(type => <div className="ticket-type" key={type.id}><div><h3>{type.name}</h3><p>{money(type.price_minor, type.currency)} <span className="muted">· {availability.data?.ticket_types.find(bucket => bucket.ticket_type_id === type.id)?.available ?? '…'} available</span></p></div>{type.kind === 'GENERAL' ? <label className="quantity-label">Quantity<input type="number" min={0} max={type.per_order_limit} value={quantities[type.id] ?? 0} onChange={e => setQuantities({ ...quantities, [type.id]: Math.max(0, Math.min(type.per_order_limit, Number(e.target.value))) })} /></label> : <div className="seat-grid" role="group" aria-label={`Seats for ${type.name}`}>{availability.data?.seats.filter(seat => seat.section_id === type.section_id).map(seat => <button className={`seat ${seats.includes(seat.id) ? 'selected' : ''}`} key={seat.id} aria-pressed={seats.includes(seat.id)} aria-label={`${seat.label}${seat.accessible ? ', accessible' : ''}, ${seat.state.toLowerCase()}`} disabled={seat.state !== 'AVAILABLE'} onClick={() => setSeats(seats.includes(seat.id) ? seats.filter(value => value !== seat.id) : [...seats, seat.id])}>{seat.label}{seat.accessible && <span aria-hidden="true"> ♿</span>}</button>)}</div>}</div>)}<p className="hint">Seats: selected = green · unavailable = grey. All seat buttons support keyboard navigation.</p>{!user ? <Link className="primary button full" to="/account">Sign in to reserve</Link> : !user.email_verified_at ? <div className="notice">Verify your email in <Link to="/account">your account</Link> before reserving.</div> : <button className="primary full" disabled={busy || detail.status !== 'PUBLISHED'} onClick={() => void selectTickets()}>Hold selected tickets ↗</button>}</>}
    </section></div></>;
}
