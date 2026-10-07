import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { Availability, Order, Payment, Reservation, TicketEvent } from '../../packages/api-client/src';
import { money, newKey, post, remainingSeconds } from '../../packages/api-client/src';
import { useSession } from './session';
import { Alert, Countdown, Field, Form, Loading, humanDate } from './ui';
import { Icon } from './Icon';

export default function EventPage() {
  const { id } = useParams(); const { user, api } = useSession(); const queries = useQueryClient();
  const event = useQuery({ queryKey: ['event', id], queryFn: () => api<TicketEvent>(`/events/${id}/`) });
  const availability = useQuery({ queryKey: ['availability', id], queryFn: () => api<Availability>(`/events/${id}/availability/`), refetchInterval: 10000 });
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [seats, setSeats] = useState<string[]>([]); const [hold, setHold] = useState<Reservation | null>(null);
  const [snapshot, setSnapshot] = useState<Order | null>(null); const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null);
  const [provider, setProvider] = useState('MOCK'); const [scenario, setScenario] = useState('success');
  const lastRequest = useRef<{ payload: string; key: string } | null>(null);
  const checkoutRequest = useRef<{ payload: string; key: string } | null>(null);
  const paymentKey = useRef(newKey());
  const liveOrder = useQuery({ queryKey: ['checkout-order', user?.id, snapshot?.id], queryFn: () => api<Order>(`/orders/${snapshot!.id}/`), enabled: !!snapshot && !!user, initialData: snapshot ?? undefined, refetchInterval: query => query.state.data?.status === 'PAYMENT_PROCESSING' ? 3000 : false });
  const order = liveOrder.data ?? snapshot;
  function updateOrder(value: Order) { setSnapshot(value); queries.setQueryData(['checkout-order', user?.id, value.id], value); }
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  useEffect(() => {
    let active = true; let socket: WebSocket | undefined; let retry: ReturnType<typeof setTimeout>;
    const refresh = () => { void queries.invalidateQueries({ queryKey: ['availability', id] }); };
    function connect() {
      if (!active || typeof WebSocket === 'undefined') return;
      const url = new URL(`/ws/events/${id}/availability/`, window.location.href); url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      socket = new WebSocket(url); socket.onopen = refresh; socket.onmessage = refresh;
      socket.onclose = () => { if (active) retry = setTimeout(connect, 5000); };
    }
    connect(); return () => { active = false; clearTimeout(retry); socket?.close(); };
  }, [id, queries]);
  function resetSelection() { setHold(null); setSnapshot(null); lastRequest.current = null; checkoutRequest.current = null; setSeats([]); void queries.invalidateQueries({ queryKey: ['availability', id] }); }
  async function selectTickets() {
    setBusy(true); setError(null);
    try {
      const items = (event.data?.ticket_types ?? []).flatMap(type => type.kind === 'GENERAL' ? quantities[type.id] ? [{ ticket_type_id: type.id, quantity: quantities[type.id] }] : [] : seats.filter(seatId => availability.data?.seats.find(seat => seat.id === seatId)?.section_id === type.section_id).map(event_seat_id => ({ ticket_type_id: type.id, event_seat_id, quantity: 1 })));
      if (!items.length) throw new Error('Select at least one ticket or seat.');
      const payload = JSON.stringify({ event_id: id, items });
      if (lastRequest.current?.payload !== payload) lastRequest.current = { payload, key: newKey() };
      setHold(await api<Reservation>('/reservations/', post(JSON.parse(payload), lastRequest.current.key))); setSnapshot(null); paymentKey.current = newKey(); checkoutRequest.current = null;
      await queries.invalidateQueries({ queryKey: ['availability', id] });
    } catch (err) { setError(err); } finally { setBusy(false); }
  }
  async function checkout(data: FormData) {
    if (!hold || !remainingSeconds(hold.expires_at)) return; setBusy(true); setError(null);
    try {
      const payload = JSON.stringify({ reservation_id: hold.id, promotion_code: String(data.get('promotion_code') ?? '') });
      if (checkoutRequest.current?.payload !== payload) checkoutRequest.current = { payload, key: newKey() };
      updateOrder(await api<Order>('/orders/', post(JSON.parse(payload), checkoutRequest.current.key)));
    } catch (err) { setError(err); } finally { setBusy(false); }
  }
  async function pay() {
    if (!order) return; setBusy(true); setError(null);
    try {
      const payment = await api<Payment>(`/orders/${order.id}/payments/`, post({ provider, scenario }, paymentKey.current));
      if (payment.checkout_url) window.location.assign(payment.checkout_url);
      updateOrder(await api<Order>(`/orders/${order.id}/`)); await queries.invalidateQueries();
    } catch (err) { setError(err); } finally { setBusy(false); }
  }
  async function completeDemo() {
    const payment = order?.payments.find(value => value.provider === 'MOCK' && value.status === 'PENDING');
    if (!order || !payment) return; setBusy(true); setError(null);
    try { await api(`/orders/${order.id}/simulate-payment/`, post({ payment_id: payment.id, outcome: 'SUCCEEDED' }, newKey())); updateOrder(await api<Order>(`/orders/${order.id}/`)); await queries.invalidateQueries(); }
    catch (err) { setError(err); } finally { setBusy(false); }
  }
  async function cancel() {
    if (!hold) return; setBusy(true); setError(null);
    try { await api(`/reservations/${hold.id}/cancel/`, post({})); resetSelection(); }
    catch (err) { setError(err); } finally { setBusy(false); }
  }
  if (event.isPending) return <Loading />;
  if (!event.data) return <Alert error={event.error} />;
  const detail = event.data; const expired = !!hold && remainingSeconds(hold.expires_at, now) === 0;
  const terminal = order && ['FAILED', 'EXPIRED', 'CANCELLED'].includes(order.status ?? '');
  const selection = detail.ticket_types.map(type => ({ type, count: type.kind === 'GENERAL' ? quantities[type.id] ?? 0 : seats.filter(seatId => availability.data?.seats.find(seat => seat.id === seatId)?.section_id === type.section_id).length }));
  const count = selection.reduce((total, item) => total + item.count, 0); const total = selection.reduce((sum, item) => sum + item.count * item.type.price_minor, 0);
  const step = order?.status === 'PAID' ? 3 : order ? 2 : hold ? 1 : 0;
  return <><Link className="back-link" to="/"><Icon name="arrow" /> All events</Link>
    <section className="event-detail-hero"><p className="eyebrow">{detail.category} · {detail.city}</p><h1>{detail.title}</h1><div className="event-facts"><span><Icon name="calendar" />{humanDate(detail.start_at, detail.event_timezone)}</span><span><Icon name="pin" />{detail.venue_name}</span><span className="pill">{detail.status}</span></div></section>
    <div className="detail-grid"><section><h2>A little about the event</h2><p className="description">{detail.description}</p><div className="info-box"><p className="eyebrow">Before you arrive</p><h3>The details</h3><p>{detail.venue_name} · {detail.city}</p><p>{detail.age_policy}</p><p>{detail.cancellation_policy}</p></div><div className="info-box"><Icon name="shield" size={28} /><h3>Your place, protected.</h3><p>Exclusive seat holds, account-only tickets and live availability. This portfolio uses test transactions, never real money.</p><Link to="/account">Your ticket wallet <Icon name="arrowUp" size={16} /></Link></div></section>
    <section className="panel checkout-panel"><ol className="checkout-steps" aria-label="Reservation progress">{['Select', 'Hold', 'Payment', 'Ready'].map((label, index) => <li key={label} className={index <= step ? 'active' : ''} aria-current={index === step ? 'step' : undefined}><span>{index < step ? <Icon name="check" size={14} /> : index + 1}</span>{label}</li>)}</ol><h2>Choose your tickets</h2><Alert error={error ?? availability.error ?? liveOrder.error} />
      {order?.status === 'PAID' ? <div className="notice"><div className="success-mark"><Icon name="check" size={32} /></div><h3>You’re going!</h3><p>Your test payment is complete. Your tickets are ready in your wallet.</p><Link className="primary button" to="/account">View my tickets <Icon name="arrow" /></Link></div> : terminal ? <div className="alert"><h3>{order.status === 'FAILED' ? 'Payment declined' : 'Reservation closed'}</h3><p>No new tickets can be issued from this reservation. Select tickets again to retry.</p><button onClick={resetSelection}>Choose again</button></div> : hold ? <><Countdown expiresAt={hold.expires_at} /><ul className="summary-list">{hold.items.map(item => <li key={item.id}>{item.quantity} × {item.name}<strong>{money(item.quantity * item.unit_price_minor, item.currency)}</strong></li>)}</ul>
        {!order ? <Form title="Continue to checkout" onSubmit={checkout} busy={busy} disabled={expired}><Field label="Promotion code" name="promotion_code" required={false} /></Form> : <><dl className="price-breakdown"><dt>Subtotal</dt><dd>{money(order.subtotal_minor, order.currency)}</dd><dt>Discount</dt><dd>−{money(order.discount_minor ?? 0, order.currency)}</dd><dt>Total</dt><dd><strong>{money(order.total_minor, order.currency)}</strong></dd></dl><p className="demo-note">Test transactions only. No real money is charged.</p>
          {order.status === 'PAYMENT_PROCESSING' ? <div className="notice" role="status"><p>Payment pending. Checking its status automatically; your original hold deadline still applies.</p><button disabled={busy} onClick={() => void liveOrder.refetch()}>Check payment status</button>{order.payments.some(payment => payment.provider === 'MOCK' && payment.status === 'PENDING') && <button disabled={busy || expired} onClick={() => void completeDemo()}>Complete demo payment</button>}</div> : <><label>Payment method<select value={provider} onChange={e => { setProvider(e.target.value); paymentKey.current = newKey(); }}><option value="MOCK">Simulated payment</option><option value="STRIPE_TEST">Stripe test checkout (if enabled)</option></select></label>{provider === 'MOCK' && <label>Demo scenario<select value={scenario} onChange={e => { setScenario(e.target.value); paymentKey.current = newKey(); }}><option value="success">Successful payment</option><option value="decline">Declined payment</option><option value="pending">Pending payment</option><option value="delayed">Delayed payment</option><option value="timeout">Timeout</option></select></label>}<button className="primary full" disabled={busy || expired} onClick={() => void pay()}>{busy ? 'Processing…' : `Pay ${money(order.total_minor, order.currency)} in test mode`} <Icon name="shield" size={18} /></button></>}
        </>}<button className="quiet full" disabled={busy} onClick={() => void cancel()}>Release tickets and start again</button></> : <><p className="muted">Select general admission or your exact seats. Tickets are held for 10 minutes.</p>{detail.ticket_types.map(type => <div className="ticket-type" key={type.id}><div><h3>{type.name}</h3><p>{money(type.price_minor, type.currency)} <span className="muted">· {availability.data?.ticket_types.find(bucket => bucket.ticket_type_id === type.id)?.available ?? '…'} available</span></p></div>
          {type.kind === 'GENERAL' ? <label className="quantity-label">Quantity<input type="number" min={0} max={type.per_order_limit} step={1} value={quantities[type.id] ?? 0} onChange={e => { const value = Number(e.target.value); setQuantities({ ...quantities, [type.id]: Number.isFinite(value) ? Math.max(0, Math.min(type.per_order_limit, Math.floor(value))) : 0 }); }} /></label> : <><div className="stage">STAGE / FRONT</div><div className="seat-grid" role="group" aria-label={`Seats for ${type.name}`}>{availability.data?.seats.filter(seat => seat.section_id === type.section_id).map(seat => <button className={`seat ${seats.includes(seat.id) ? 'selected' : ''}`} key={seat.id} aria-pressed={seats.includes(seat.id)} aria-label={`${seat.label}${seat.accessible ? ', accessible' : ''}, ${seat.state.toLowerCase()}`} disabled={seat.state !== 'AVAILABLE' || !seats.includes(seat.id) && (selection.find(item => item.type.id === type.id)?.count ?? 0) >= type.per_order_limit} onClick={() => setSeats(seats.includes(seat.id) ? seats.filter(value => value !== seat.id) : [...seats, seat.id])}>{seat.label}{seat.accessible && <span aria-hidden="true"> ♿</span>}</button>)}</div></>}
        </div>)}{detail.ticket_types.some(type => type.kind === 'ASSIGNED') && <div className="seat-legend"><span><i />Available</span><span><i className="chosen" />Selected</span><span><i className="unavailable" />Unavailable</span></div>}<p className="hint">All seat buttons support keyboard navigation. Availability is confirmed when you reserve.</p>{count > 0 && <div className="selection-total"><span>{count} {count === 1 ? 'ticket' : 'tickets'} selected</span><strong>{money(total, detail.ticket_types[0]?.currency)}</strong></div>}
        {!user ? <Link className="primary button full" to="/account">Sign in to reserve</Link> : !user.email_verified_at ? <div className="notice">Verify your email in <Link to="/account">your account</Link> before reserving.</div> : <button className="primary full" disabled={busy || !count || detail.status !== 'PUBLISHED'} onClick={() => void selectTickets()}>Hold selected tickets ↗</button>}</>}
    </section></div></>;
}
