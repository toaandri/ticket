import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { Organization, Tokens, User, request } from './api';

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const tokens = useRef<Tokens | null>(null);

  const loadOrganizations = useCallback(async () => {
    if (!tokens.current) return;
    const result = await request<{ results: Organization[] }>('/organizations/', {}, tokens.current.access);
    setOrganizations(result.results);
  }, []);

  useEffect(() => {
    if (!user) return;
    void loadOrganizations().catch((err: Error) => setError(err.message));
  }, [user, loadOrganizations]);

  async function authenticate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError(''); setNotice('');
    const form = new FormData(event.currentTarget);
    try {
      const result = await request<Tokens>(`/auth/${mode}/`, {
        method: 'POST', body: JSON.stringify({ email: form.get('email'), password: form.get('password'),
          ...(mode === 'register' ? { display_name: form.get('display_name') } : {}) }),
      });
      tokens.current = result;
      setUser(await request<User>('/me/', {}, result.access));
    } catch (err) { tokens.current = null; setError((err as Error).message); }
    finally { setBusy(false); }
  }

  async function createOrganization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const element = event.currentTarget;
    const form = new FormData(element);
    setBusy(true); setError(''); setNotice('');
    try {
      // Refresh before writes; rotated refresh tokens stay in memory only.
      if (!tokens.current) throw new Error('Please sign in again.');
      tokens.current = await request<Tokens>('/auth/refresh/', { method: 'POST', body: JSON.stringify({ refresh: tokens.current.refresh }) });
      const organization = await request<Organization>('/organizations/', { method: 'POST',
        body: JSON.stringify({ name: form.get('name'), slug: form.get('slug') }) }, tokens.current.access);
      await loadOrganizations(); element.reset(); setNotice(`${organization.name} created.`);
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  async function logout() {
    setError('');
    try {
      if (tokens.current) {
        tokens.current = await request<Tokens>('/auth/refresh/', { method: 'POST', body: JSON.stringify({ refresh: tokens.current.refresh }) });
        await request<void>('/auth/logout/', { method: 'POST', body: JSON.stringify({ refresh: tokens.current.refresh }) }, tokens.current.access);
      }
    } catch (err) { setNotice(`Signed out locally. Server sign-out failed: ${(err as Error).message}`); }
    finally { tokens.current = null; setUser(null); setOrganizations([]); }
  }

  return <div className="app">
    <header className="topbar"><a className="brand" href="/">Ticket<span className="brand-dot">.</span></a>
      <span className="tag">Event workspace</span>
      {user && <button className="quiet" onClick={() => void logout()}>Sign out</button>}
    </header>
    <main>
      {error && <div className="alert" role="alert">{error}</div>}
      {notice && <div className="notice" role="status">{notice}</div>}
      {!user ? <div className="welcome">
        <section className="intro"><p className="eyebrow">Start with your team</p><h1>A home for your next event.</h1>
          <p>Create an account and set up your organization’s workspace.</p>
          <div className="feature"><span aria-hidden="true">01</span><div><strong>Your account</strong><p>One profile for your event teams.</p></div></div>
          <div className="feature"><span aria-hidden="true">02</span><div><strong>Your organization</strong><p>A dedicated workspace for each team.</p></div></div>
        </section>
        <section className="panel" aria-labelledby="auth-title"><h2 id="auth-title">{mode === 'login' ? 'Welcome back' : 'Create your account'}</h2>
          <p className="muted">{mode === 'login' ? 'Sign in to your workspace.' : 'Start organizing with your team.'}</p>
          <form onSubmit={event => void authenticate(event)}>
            {mode === 'register' && <label>Display name<input name="display_name" autoComplete="name" maxLength={150} /></label>}
            <label>Email<input name="email" type="email" required autoComplete="email" /></label>
            <label>Password<input name="password" type="password" required autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={mode === 'register' ? 8 : undefined} /></label>
            <button className="primary" disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}</button>
          </form>
          <button className="switch" disabled={busy} onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}>
            {mode === 'login' ? 'New here? Create an account' : 'Already have an account? Sign in'}
          </button>
        </section>
      </div> : <div className="dashboard">
        <section className="dashboard-heading"><p className="eyebrow">Your workspace</p><h1>Hello, {user.display_name || user.email}.</h1><p className="muted">Manage the organizations you belong to.</p></section>
        <div className="dashboard-grid"><section aria-labelledby="organizations-title"><h2 id="organizations-title">Your organizations</h2>
          {organizations.length ? <ul className="org-list">{organizations.map(org => <li className="org" key={org.id}><span className="org-icon" aria-hidden="true">{org.name.charAt(0).toUpperCase()}</span><div><h3>{org.name}</h3><p className="muted">{org.slug}</p></div></li>)}</ul> : <div className="empty"><h3>Your first workspace starts here.</h3><p>Create an organization to get started.</p></div>}
        </section><section className="panel" aria-labelledby="new-org-title"><h2 id="new-org-title">Create an organization</h2><form onSubmit={event => void createOrganization(event)}>
          <label>Organization name<input name="name" required maxLength={200} /></label>
          <label>Workspace slug<input name="slug" required pattern="[a-zA-Z0-9_-]+" maxLength={50} aria-describedby="slug-help" /></label><p id="slug-help" className="hint">Use letters, numbers, hyphens or underscores.</p>
          <button className="primary" disabled={busy}>{busy ? 'Creating…' : 'Create workspace'}</button>
        </form></section></div>
      </div>}
    </main><footer>Ticket · Bring your team together.</footer>
  </div>;
}
