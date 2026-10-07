import { useEffect, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Network from 'expo-network';
import { randomUUID } from 'expo-crypto';
import type { CheckIn, Paginated, TicketEvent } from '../../packages/api-client/src';
import { post } from '../../packages/api-client/src';
import { ApiError } from '../src/api';
import { useSession } from '../src/session';
import { Alert, Button, Input, Loading, Page, SignInPrompt, styles } from '../src/ui';

export default function Scanner() {
  const { user } = useSession();
  return <ScannerSession key={user?.id ?? 'guest'} />;
}
function ScannerSession() {
  const { user, ready, api } = useSession(); const [permission, requestPermission] = useCameraPermissions(); const [eventId, setEventId] = useState(''); const [token, setToken] = useState(''); const [camera, setCamera] = useState(false); const [result, setResult] = useState<CheckIn | null>(null); const [error, setError] = useState<unknown>(null); const [busy, setBusy] = useState(false); const lock = useRef(false); const lastRequest = useRef<{ payload: string; key: string } | null>(null);
  const events = useQuery({ queryKey: ['staff-events', user?.id], queryFn: () => api<Paginated<TicketEvent>>('/staff/events/'), enabled: !!user });
  useEffect(() => { return () => { lock.current = false; }; }, []);
  async function scan(value: string) { if (lock.current) return; lock.current = true; setBusy(true); setCamera(false); setError(null); setResult(null); try { const network = await Network.getNetworkStateAsync(); if (!network.isConnected || network.isInternetReachable === false) throw new Error('Offline. Admission cannot be confirmed. Reconnect and scan again.'); if (!eventId || !value.trim()) throw new Error('Choose an assigned event and enter a QR token or URL.'); const payload = JSON.stringify({ event_id: eventId, token: value.trim(), device_id: 'ticket-expo' }); if (lastRequest.current?.payload !== payload) lastRequest.current = { payload, key: randomUUID() }; const response = await api<CheckIn>('/check-ins/', post(JSON.parse(payload), lastRequest.current.key)); setResult(response); lastRequest.current = null; } catch (err) { if (err instanceof ApiError && err.status === 409 && err.data && typeof err.data === 'object' && 'result' in err.data) { setResult(err.data as CheckIn); lastRequest.current = null; } else setError(err); } finally { lock.current = false; setBusy(false); } }
  if (!ready) return <Page title="Gate scanner"><Loading /></Page>; if (!user) return <Page title="Gate scanner"><SignInPrompt /></Page>;
  return <Page title="Gate scanner"><Text style={styles.notice}>Online admission only. A green ACCEPTED response from the server is required.</Text><Alert error={error ?? events.error} />{events.isPending && <Loading />}{events.data?.results.length === 0 && <Text style={styles.muted}>No assigned events. Ask your organizer to assign your Scanner membership to an event.</Text>}{events.data?.results.map(event => <Button key={event.id} title={`${eventId === event.id ? 'Selected: ' : ''}${event.title}`} disabled={busy} onPress={() => { setEventId(event.id); setResult(null); lastRequest.current = null; }} />)}{eventId && <><Input label="QR token or ticket URL" value={token} onChangeText={setToken} /><Button title="Check admission" disabled={busy || !token.trim()} onPress={() => void scan(token)} /><Button title="Scan with camera" disabled={busy} onPress={() => { void (permission?.granted ? Promise.resolve(permission) : requestPermission()).then(value => { if (value.granted) { setResult(null); setCamera(true); } else setError(new Error('Camera permission denied. Enter the QR token manually.')); }).catch(setError); }} />{camera && <><CameraView style={{ height: 300, borderRadius: 12 }} facing="back" barcodeScannerSettings={{ barcodeTypes: ['qr'] }} onBarcodeScanned={({ data }) => void scan(data)} /><Button title="Close camera" onPress={() => setCamera(false)} /></>}{result && <View style={styles.card}><Text accessibilityRole="alert" style={result.result === 'ACCEPTED' ? styles.notice : styles.error}>{result.result === 'ACCEPTED' ? 'ACCEPTED — Admit one person' : `${result.result} — Do not admit`}</Text><Text style={styles.muted}>Server scan {result.id}</Text></View>}</>}</Page>;
}
