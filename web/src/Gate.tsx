import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { CheckIn, Paginated, TicketEvent } from '../../packages/api-client/src';
import { newKey, post } from '../../packages/api-client/src';
import { ApiError } from './api';
import { useSession } from './session';
import { Alert, Empty, RequireLogin } from './ui';

export default function Gate() {
  const { user, api } = useSession(); const [eventId, setEventId] = useState(''); const [token, setToken] = useState(new URLSearchParams(window.location.search).get('token') ?? '');
  const [error, setError] = useState<unknown>(null); const [result, setResult] = useState<CheckIn | null>(null); const [busy, setBusy] = useState(false); const [camera, setCamera] = useState(false);
  const video = useRef<HTMLVideoElement>(null); const stream = useRef<MediaStream | null>(null); const requestKey = useRef<{ payload: string; key: string } | null>(null);
  const events = useQuery({ queryKey: ['staff-events', user?.id], queryFn: () => api<Paginated<TicketEvent>>('/staff/events/'), enabled: !!user });
  useEffect(() => () => { stream.current?.getTracks().forEach(track => track.stop()); }, []);
  async function scan(value: string) {
    if (!eventId || !value.trim()) { setError(new Error('Choose an assigned event and enter a QR token.')); return; }
    if (!navigator.onLine) { setError(new Error('Online connection required. Offline admissions are unavailable.')); return; }
    setBusy(true); setError(null); setResult(null); setCamera(false); stream.current?.getTracks().forEach(track => track.stop());
    const payload = JSON.stringify({ event_id: eventId, token: value, device_id: 'web-gate' });
    if (requestKey.current?.payload !== payload) requestKey.current = { payload, key: newKey() };
    try {
      const response = await api<CheckIn>('/check-ins/', post(JSON.parse(payload), requestKey.current.key)); setResult(response); requestKey.current = null;
    } catch (err) {
      // Gate conflicts use the typed CheckIn body to distinguish rejected scans.
      if (err instanceof ApiError && err.status === 409 && typeof err.data === 'object' && err.data !== null && 'result' in err.data) { setResult(err.data as CheckIn); requestKey.current = null; } else setError(err);
    } finally { setBusy(false); }
  }
  async function startCamera() {
    setError(null);
    type BarcodeConstructor = new (options: { formats: string[] }) => { detect: (source: HTMLVideoElement) => Promise<{ rawValue: string }[]> };
    const Barcode = (window as unknown as { BarcodeDetector?: BarcodeConstructor }).BarcodeDetector;
    if (!Barcode || !navigator.mediaDevices) { setError(new Error('Camera QR detection is unavailable in this browser. Use manual entry or the native scanner.')); return; }
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } }); setCamera(true);
      const detector = new Barcode({ formats: ['qr_code'] });
      const detect = async () => {
        if (!stream.current?.active) return;
        if (video.current && video.current.readyState >= 2) {
          const codes = await detector.detect(video.current); if (codes[0]) { setToken(codes[0].rawValue); await scan(codes[0].rawValue); return; }
        }
        requestAnimationFrame(() => { void detect().catch(setError); });
      };
      requestAnimationFrame(() => { if (video.current && stream.current) { video.current.srcObject = stream.current; void video.current.play(); void detect().catch(setError); } });
    } catch (err) { setError(err); }
  }
  if (!user) return <RequireLogin />;
  return <div className="gate-page"><p className="eyebrow">Keep the line moving</p><h1>Gate scanner</h1><p className="muted">Online verification only. Scan tickets for your assigned events.</p><Alert error={error ?? events.error} />{events.data && !events.data.results.length && <Empty>You have no events assigned for scanning. Ask your organization owner.</Empty>}<section className="panel narrow"><label>Assigned event<select value={eventId} onChange={e => { setEventId(e.target.value); setResult(null); }}><option value="">Choose an event</option>{events.data?.results.map(event => <option key={event.id} value={event.id}>{event.title}</option>)}</select></label><button disabled={busy || !eventId} onClick={() => void startCamera()}>Use camera</button>{camera && <><video ref={video} playsInline muted aria-label="QR scanning camera" /><button onClick={() => { stream.current?.getTracks().forEach(track => track.stop()); setCamera(false); }}>Stop camera</button></>}<form onSubmit={e => { e.preventDefault(); void scan(token); }}><label>QR token or ticket URL<textarea value={token} onChange={e => setToken(e.target.value)} required /></label><button className="primary full" disabled={busy || !eventId}>{busy ? 'Checking…' : 'Check admission'}</button></form>{result && <div role="status" className={`scan-result ${result.result === 'ACCEPTED' ? 'accepted' : 'rejected'}`}><strong>{result.result === 'ACCEPTED' ? '✓ Accepted — admit attendee' : result.result === 'DUPLICATE' ? 'Already admitted — duplicate scan' : result.result === 'CLOSED' ? 'Check-in window is closed' : `${result.result} — do not admit`}</strong><p>{new Date(result.created_at).toLocaleTimeString()}</p></div>}</section></div>;
}
