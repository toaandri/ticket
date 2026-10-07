import { useEffect, useState } from 'react';
import { BrowserRouter, Link, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SessionProvider, useSession } from './session';
import Discover from './Discover';
import EventPage from './EventPage';
import Account from './Account';
import Workspace from './Workspace';
import Gate from './Gate';
import Admin from './Admin';
import Saved from './Saved';
import SearchDialog from './SearchDialog';
import { Icon } from './Icon';
import { Alert } from './ui';

const queries = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 10000 } } });
function Shell() {
  const { user, logout } = useSession(); const [error, setError] = useState<unknown>(null); const location = useLocation();
  const [theme, setTheme] = useState<'light' | 'dark'>(() => { try { return localStorage.getItem('ticket.theme') === 'dark' ? 'dark' : 'light'; } catch { return 'light'; } });
  const [motion, setMotion] = useState(true);
  useEffect(() => { document.documentElement.dataset.motion = motion ? 'on' : 'off'; }, [motion]);
  useEffect(() => { document.documentElement.dataset.theme = theme; }, [theme]);
  useEffect(() => { if (typeof window.scrollTo === 'function') window.scrollTo({ top: 0, behavior: 'instant' }); setError(null); }, [location.pathname]);
  function toggleTheme() { const next = theme === 'light' ? 'dark' : 'light'; setTheme(next); try { localStorage.setItem('ticket.theme', next); } catch { /* Theme also works without storage. */ } }
  return <div className="app"><a className="skip-link" href="#main">Skip to content</a>
    <header className="topbar"><div className="topbar-inner"><Link className="brand" to="/" aria-label="Ticket home"><span className="brand-mark"><Icon name="ticket" size={22} /></span>ticket<span className="brand-dot">.</span></Link>
      <nav aria-label="Main navigation"><NavLink to="/" end><Icon name="compass" size={17} />Discover</NavLink><NavLink to="/saved"><Icon name="heart" size={17} />Saved</NavLink><NavLink to="/account"><Icon name="ticket" size={17} />My tickets</NavLink><NavLink to="/workspace"><Icon name="grid" size={17} />Workspace</NavLink>{user?.is_superuser && <NavLink to="/admin">Admin</NavLink>}</nav>
      <div className="header-actions"><SearchDialog /><button className="icon-button" aria-label={motion ? 'Pause animations' : 'Resume animations'} aria-pressed={!motion} onClick={() => setMotion(!motion)}><Icon name={motion ? 'sparkle' : 'clock'} size={18} /></button><button className="icon-button" aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`} onClick={toggleTheme}><Icon name={theme === 'light' ? 'moon' : 'sun'} size={18} /></button>{user ? <button className="account-button" aria-label="Sign out" title={`Signed in as ${user.display_name || user.email}. Sign out`} onClick={() => void logout().catch(setError)}><span className="avatar">{(user.display_name || user.email)[0].toUpperCase()}</span><span>Sign out</span></button> : <Link className="primary button sign-in" to="/account">Sign in <Icon name="arrowUp" size={16} /></Link>}</div>
    </div></header>
    <main id="main"><Alert error={error} /><div className="page-scene" key={`${location.pathname}:${user?.id ?? 'guest'}`}><Routes><Route path="/" element={<Discover />} /><Route path="/saved" element={<Saved />} /><Route path="/events/:id" element={<EventPage />} /><Route path="/account" element={<Account />} /><Route path="/workspace" element={<Workspace />} /><Route path="/gate" element={<Gate />} /><Route path="/admin" element={<Admin />} /><Route path="*" element={<div className="empty page-heading"><Icon name="compass" size={48} /><p className="eyebrow">A little off the map</p><h1>Page not found</h1><Link className="primary button" to="/">Discover events <Icon name="arrow" /></Link></div>} /></Routes></div></main>
    <footer><div className="footer-top"><Link className="brand" to="/">ticket.</Link><h2>Less scrolling.<br /><em>More being there.</em></h2><Link className="footer-link" to="/workspace">Make something happen <Icon name="arrowUp" /></Link></div><div className="footer-bottom"><p>Good moments, together.</p><span>Portfolio demo · Synthetic events · Simulated transactions</span><span>Built for people.</span></div></footer>
  </div>;
}
export default function App() { return <QueryClientProvider client={queries}><BrowserRouter><SessionProvider><Shell /></SessionProvider></BrowserRouter></QueryClientProvider>; }
