import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { remainingSeconds } from '../../packages/api-client/src';

export function Alert({ error }: { error: unknown }) { return error ? <p className="alert" role="alert">{error instanceof Error ? error.message : String(error)}</p> : null; }
export function Loading() { return <p role="status" className="muted">Loading…</p>; }
export function Empty({ children }: { children: ReactNode }) { return <div className="empty">{children}</div>; }
export function RequireLogin() { return <Empty><h2>Sign in to continue</h2><p>Your tickets and checkout belong to your account.</p><Link className="primary button" to="/account">Sign in</Link></Empty>; }
export function Countdown({ expiresAt }: { expiresAt: string }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  const seconds = remainingSeconds(expiresAt, now);
  return <p className="countdown" role="timer">{seconds ? `Held for ${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}` : 'Your hold has expired. Select tickets again.'}</p>;
}
export function Form({ title, children, onSubmit, busy = false }: { title: string; children: ReactNode; onSubmit: (data: FormData, form: HTMLFormElement) => Promise<void>; busy?: boolean }) {
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const element = event.currentTarget; await onSubmit(new FormData(element), element);
  }
  return <form className="stack" onSubmit={event => void submit(event)} aria-label={title}><h3>{title}</h3><fieldset disabled={busy}>{children}<button className="primary" type="submit">{busy ? 'Please wait…' : title}</button></fieldset></form>;
}
export function Field({ label, name, type = 'text', required = true, value }: { label: string; name: string; type?: string; required?: boolean; value?: string }) {
  return <label>{label}<input name={name} type={type} required={required} defaultValue={value} min={type === 'number' ? 0 : undefined} /></label>;
}
export function humanDate(value: string, zone?: string) { return new Intl.DateTimeFormat('en', { dateStyle: 'medium', timeStyle: 'short', timeZone: zone }).format(new Date(value)); }
