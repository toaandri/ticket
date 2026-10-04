import { BrowserRouter, Link, NavLink, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SessionProvider, useSession } from './session';
import Discover from './Discover';
import EventPage from './EventPage';
import Account from './Account';
import Workspace from './Workspace';
import Gate from './Gate';
import Admin from './Admin';
import { useState } from 'react';
import { Alert } from './ui';

const queries = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 10000 } } });
function Shell() {
  const { user, logout } = useSession(); const [error, setError] = useState<unknown>(null);
  return <div className="app"><a className="skip-link" href="#main">Skip to content</a><header className="topbar"><Link className="brand" to="/">Ticket<span className="brand-dot">.</span></Link><nav aria-label="Main navigation"><NavLink to="/" end>Discover</NavLink><NavLink to="/account">My tickets</NavLink><NavLink to="/workspace">Workspace</NavLink>{user?.is_superuser && <NavLink to="/admin">Admin</NavLink>}</nav>{user ? <button className="quiet" onClick={() => void logout().catch(setError)}>Sign out</button> : <Link className="primary button" to="/account">Sign in ↗</Link>}</header><main id="main"><Alert error={error} /><Routes><Route path="/" element={<Discover />} /><Route path="/events/:id" element={<EventPage />} /><Route path="/account" element={<Account />} /><Route path="/workspace" element={<Workspace />} /><Route path="/gate" element={<Gate />} /><Route path="/admin" element={<Admin />} /><Route path="*" element={<div className="empty"><h1>Page not found</h1><Link to="/">Discover events</Link></div>} /></Routes></main><footer><Link className="brand" to="/">Ticket.</Link><p>Good moments, together.</p><span>Portfolio demo · All transactions are simulated.</span></footer></div>;
}
export default function App() {
  return <QueryClientProvider client={queries}><BrowserRouter><SessionProvider><Shell /></SessionProvider></BrowserRouter></QueryClientProvider>;
}
