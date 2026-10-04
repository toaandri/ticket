import { useEffect, useState } from 'react';
import { useInfiniteQuery, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import type { Notification, Order, Paginated, Profile, Ticket } from '../../packages/api-client/src';
import { money, post } from '../../packages/api-client/src';
import { useSession } from './session';
import { Alert, Empty, Field, Form, Loading, humanDate } from './ui';

export function AuthForm() {
  const { login, api } = useSession(); const [register, setRegister] = useState(false); const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null); const [notice, setNotice] = useState('');
  async function signIn(data: FormData) {
    setBusy(true); setError(null);
    try { await login(String(data.get('email')), String(data.get('password')), register ? String(data.get('display_name') ?? '') : undefined); }
    catch (err) { setError(err); } finally { setBusy(false); }
  }
  async function reset(data: FormData) {
    setBusy(true); setError(null);
    try { await api('/auth/password-reset/', post({ email: data.get('reset_email') })); setNotice('If this account exists, a reset link will arrive by email.'); }
    catch (err) { setError(err); } finally { setBusy(false); }
  }
  return <div className="auth-layout"><div className="intro"><p className="eyebrow">Your next good moment</p><h1>One account.<br />All your events.</h1><p>Save your place, keep your tickets close and bring your team together.</p></div><div className="panel"><Alert error={error} />{notice && <p className="notice" role="status">{notice}</p>}<Form title={register ? 'Create account' : 'Sign in'} onSubmit={signIn} busy={busy}>{register && <Field label="Display name" name="display_name" required={false} />}<Field label="Email" name="email" type="email" /><Field label="Password" name="password" type="password" /></Form><button className="switch" onClick={() => setRegister(!register)}>{register ? 'Already have an account? Sign in' : 'New here? Create an account'}</button><details><summary>Forgot your password?</summary><Form title="Send reset link" onSubmit={reset} busy={busy}><Field label="Account email" name="reset_email" type="email" /></Form></details></div></div>;
}

function TicketCard({ ticket }: { ticket: Ticket }) {
  const { api } = useSession(); const [image, setImage] = useState(''); const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    if (ticket.status !== 'VALID') return;
    let active = true; let url = '';
    void api<Blob>(`/tickets/${ticket.id}/qr/`).then(blob => { if (active) { url = URL.createObjectURL(blob); setImage(url); } }).catch(setError);
    return () => { active = false; if (url) URL.revokeObjectURL(url); };
  }, [ticket.id, ticket.status, api]);
  async function download() {
    try {
      const blob = await api<Blob>(`/tickets/${ticket.id}/pdf/`); const url = URL.createObjectURL(blob);
      const link = document.createElement('a'); link.href = url; link.download = `${ticket.public_code ?? 'ticket'}.pdf`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) { setError(err); }
  }
  return <article className="wallet-ticket"><div><p className="eyebrow">{ticket.status}</p><h3>{ticket.event_title}</h3><p>{humanDate(ticket.start_at)}</p><p>{ticket.ticket_type_name} · {ticket.seat_label || 'General admission'}</p><p className="hint">{ticket.public_code}</p><button className="quiet" onClick={() => void download()}>Download PDF ↓</button><Alert error={error} /></div>{image && <img className="qr" src={image} alt={`Admission QR for ${ticket.event_title}, ${ticket.seat_label || ticket.ticket_type_name}`} />}<div className="ticket-notch" aria-hidden="true" /></article>;
}

export default function Account() {
  const { user, api, updateProfile } = useSession(); const queries = useQueryClient(); const [params] = useSearchParams();
  const [error, setError] = useState<unknown>(null); const [notice, setNotice] = useState(''); const [busy, setBusy] = useState(false);
  const tickets = useInfiniteQuery({ queryKey: ['tickets', user?.id], initialPageParam: 1, queryFn: ({ pageParam }) => api<Paginated<Ticket>>(`/tickets/?page=${pageParam}`), getNextPageParam: (page, pages) => page.next ? pages.length + 1 : undefined, enabled: !!user });
  const orders = useInfiniteQuery({ queryKey: ['orders', user?.id], initialPageParam: 1, queryFn: ({ pageParam }) => api<Paginated<Order>>(`/orders/?page=${pageParam}`), getNextPageParam: (page, pages) => page.next ? pages.length + 1 : undefined, enabled: !!user, refetchInterval: 10000 });
  const notifications = useQuery({ queryKey: ['notifications', user?.id], queryFn: () => api<Paginated<Notification>>('/notifications/'), enabled: !!user });
  async function action(callback: () => Promise<unknown>, success: string) {
    setBusy(true); setError(null); try { await callback(); setNotice(success); await queries.invalidateQueries(); } catch (err) { setError(err); } finally { setBusy(false); }
  }
  const resetToken = params.get('reset');
  return <><Alert error={error} />{notice && <p className="notice" role="status">{notice}</p>}{resetToken ? <div className="panel narrow"><Form title="Set new password" busy={busy} onSubmit={data => action(() => api('/auth/password-reset/confirm/', post({ user_id: params.get('user_id'), token: resetToken, password: data.get('password') })), 'Password changed. Sign in with your new password.')}><Field label="New password" name="password" type="password" /></Form></div> : null}{params.get('verify') && <div className="notice"><h2>Verify your email</h2><button disabled={busy} onClick={() => void action(async () => { await api('/auth/email-verify/', post({ token: params.get('verify') })); if (user) updateProfile(await api<Profile>('/me/')); }, 'Email verified. You can now reserve tickets.')}>Confirm email verification</button></div>}
  {!user ? <AuthForm /> : <><div className="section-heading"><div><p className="eyebrow">Your account</p><h1>Hello, {user.display_name || user.email}.</h1><p className="muted">Your tickets, all in one place.</p></div><Link className="quiet button" to="/workspace">Organization workspace ↗</Link></div>{!user.email_verified_at && <div className="notice"><p>Verify {user.email} to reserve tickets and accept team invitations.</p><button disabled={busy} onClick={() => void action(() => api('/auth/email-verification/', post({})), 'Verification email queued. In the local demo, open Mailpit at localhost:8025.')}>Send verification email</button><Form title="Verify email with token" busy={busy} onSubmit={data => action(async () => { await api('/auth/email-verify/', post({ token: data.get('token') })); updateProfile(await api<Profile>('/me/')); }, 'Email verified.')}><Field label="Verification token" name="token" /></Form></div>}
  {params.get('invitation') && <div className="notice"><h2>Join your event team</h2><button disabled={busy} onClick={() => void action(() => api('/invitations/accept/', post({ token: params.get('invitation') })), 'Invitation accepted. Open your workspace.')}>Accept invitation</button></div>}
  <section><h2>My tickets</h2>{tickets.isPending ? <Loading /> : <Alert error={tickets.error} />}{tickets.data && !tickets.data.pages[0].count && <Empty><h3>Your next event is waiting.</h3><Link to="/">Find an event ↗</Link></Empty>}<div className="wallet-grid">{tickets.data?.pages.flatMap(page => page.results).map(ticket => <TicketCard key={ticket.id} ticket={ticket} />)}</div>{tickets.hasNextPage && <button onClick={() => void tickets.fetchNextPage()} disabled={tickets.isFetchingNextPage}>More tickets</button>}</section>
  <section><h2>Order history</h2><Alert error={orders.error} />{orders.data && !orders.data.pages[0].count && <p className="muted">No orders yet.</p>}<div className="table-scroll"><table><thead><tr><th>Order</th><th>Event</th><th>Status</th><th>Simulated total</th></tr></thead><tbody>{orders.data?.pages.flatMap(page => page.results).map(order => <tr key={order.id}><td>{order.public_reference}</td><td><Link to={`/events/${order.event_id}`}>{order.event_title}</Link></td><td><span className="pill subtle">{order.status}</span></td><td>{money(order.total_minor, order.currency)}</td></tr>)}</tbody></table></div>{orders.hasNextPage && <button onClick={() => void orders.fetchNextPage()} disabled={orders.isFetchingNextPage}>More orders</button>}</section>
  <div className="dashboard-grid"><section><h2>Notifications</h2><Alert error={notifications.error} />{notifications.data?.results.length ? notifications.data.results.map(notification => <article className="notification" key={notification.id}><h3>{notification.subject}</h3><p>{notification.body}</p>{!notification.read_at && <button className="quiet" onClick={() => void action(() => api(`/notifications/${notification.id}/read/`, post({})), 'Marked as read.')}>Mark as read</button>}</article>) : <p className="muted">You’re all caught up.</p>}</section><section className="panel"><Form title="Update profile" busy={busy} onSubmit={data => action(async () => updateProfile(await api<Profile>('/me/', { method: 'PATCH', body: JSON.stringify({ display_name: data.get('display_name') }) })), 'Profile updated.')}><Field label="Display name" name="display_name" value={user.display_name} required={false} /></Form><Form title="Accept invitation" busy={busy} onSubmit={data => action(() => api('/invitations/accept/', post({ token: data.get('invitation_token') })), 'Invitation accepted.')}><Field label="Invitation token" name="invitation_token" /></Form></section></div>
  </>}
  </>;
}
