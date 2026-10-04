import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Organization, Tokens, User, getRefresh, request, saveRefresh } from '../src/api';

export default function Index() {
  const [user, setUser] = useState<User | null>(null);
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');

  async function openWorkspace(tokens: Tokens) {
    await saveRefresh(tokens.refresh);
    const profile = await request<User>('/me/', {}, tokens.access);
    const list = await request<{ results: Organization[] }>('/organizations/', {}, tokens.access);
    setOrganizations(list.results); setUser(profile); setPassword('');
  }
  async function refreshSession() {
    const refresh = await getRefresh();
    if (!refresh) throw new Error('Please sign in again.');
    const tokens = await request<Tokens>('/auth/refresh/', { method: 'POST', body: JSON.stringify({ refresh }) });
    await saveRefresh(tokens.refresh);
    return tokens;
  }
  useEffect(() => {
    let active = true;
    async function restore() {
      try {
        const refresh = await getRefresh();
        if (refresh && active) {
          const tokens = await request<Tokens>('/auth/refresh/', { method: 'POST', body: JSON.stringify({ refresh }) });
          if (active) await openWorkspace(tokens);
        }
      } catch (err) { if (active) setError((err as Error).message); }
      finally { if (active) setBusy(false); }
    }
    void restore();
    return () => { active = false; };
  }, []);

  async function authenticate() {
    if (!email.trim() || !password) { setError('Enter your email and password.'); return; }
    setBusy(true); setError('');
    try {
      const tokens = await request<Tokens>(register ? '/auth/register/' : '/auth/login/', { method: 'POST',
        body: JSON.stringify({ email, password, ...(register ? { display_name: displayName } : {}) }) });
      await openWorkspace(tokens);
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }
  async function createOrganization() {
    if (!name.trim() || !slug.trim()) { setError('Enter a name and workspace slug.'); return; }
    setBusy(true); setError('');
    try {
      const tokens = await refreshSession();
      await request<Organization>('/organizations/', { method: 'POST', body: JSON.stringify({ name, slug }) }, tokens.access);
      const list = await request<{ results: Organization[] }>('/organizations/', {}, tokens.access);
      setOrganizations(list.results); setName(''); setSlug('');
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }
  async function logout() {
    setBusy(true); setError('');
    try {
      const tokens = await refreshSession();
      await request<void>('/auth/logout/', { method: 'POST', body: JSON.stringify({ refresh: tokens.refresh }) }, tokens.access);
    } catch (err) { setError(`Signed out locally. ${(err as Error).message}`); }
    finally { await saveRefresh(null); setUser(null); setOrganizations([]); setBusy(false); }
  }

  return <SafeAreaView style={styles.safe}><ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.content}>
    <Text style={styles.brand}>Ticket.</Text>
    {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
    {busy && <ActivityIndicator accessibilityLabel="Loading workspace" color="#204d36" />}
    {!user ? <View style={styles.card}>
      <Text accessibilityRole="header" style={styles.title}>{register ? 'Create your account' : 'Welcome back'}</Text>
      <Text style={styles.description}>A home for your event team.</Text>
      {register && <><Text>Display name</Text><TextInput accessibilityLabel="Display name" style={styles.input} value={displayName} onChangeText={setDisplayName} autoComplete="name" maxLength={150} /></>}
      <Text>Email</Text><TextInput accessibilityLabel="Email" style={styles.input} value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" autoComplete="email" />
      <Text>Password</Text><TextInput accessibilityLabel="Password" style={styles.input} value={password} onChangeText={setPassword} secureTextEntry autoCapitalize="none" autoComplete={register ? 'new-password' : 'current-password'} />
      <Pressable accessibilityRole="button" disabled={busy} style={styles.button} onPress={() => void authenticate()}><Text style={styles.buttonText}>{register ? 'Create account' : 'Sign in'}</Text></Pressable>
      <Pressable accessibilityRole="button" disabled={busy} onPress={() => { setRegister(!register); setError(''); }}><Text style={styles.link}>{register ? 'Already have an account? Sign in' : 'New here? Create an account'}</Text></Pressable>
    </View> : <>
      <Text accessibilityRole="header" style={styles.title}>Hello, {user.display_name || user.email}.</Text>
      <Text style={styles.description}>Your organizations</Text>
      {!organizations.length && <Text>Create your first workspace below.</Text>}
      {organizations.map(org => <View key={org.id} style={styles.organization}><Text style={styles.orgTitle}>{org.name}</Text><Text>{org.slug}</Text></View>)}
      <View style={styles.card}><Text accessibilityRole="header" style={styles.orgTitle}>Create an organization</Text>
        <Text>Organization name</Text><TextInput accessibilityLabel="Organization name" style={styles.input} value={name} onChangeText={setName} maxLength={200} />
        <Text>Workspace slug</Text><TextInput accessibilityLabel="Workspace slug" style={styles.input} value={slug} onChangeText={setSlug} autoCapitalize="none" maxLength={50} />
        <Pressable accessibilityRole="button" disabled={busy} style={styles.button} onPress={() => void createOrganization()}><Text style={styles.buttonText}>Create workspace</Text></Pressable>
      </View>
      <Pressable accessibilityRole="button" disabled={busy} onPress={() => void logout()}><Text style={styles.link}>Sign out</Text></Pressable>
    </>}
  </ScrollView></SafeAreaView>;
}
const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#f5f7f2' }, content: { padding: 24, gap: 18 },
  brand: { fontSize: 36, fontWeight: '800', color: '#152f2b', marginBottom: 20 },
  title: { fontSize: 28, fontWeight: '700', color: '#152f2b' }, description: { color: '#627566', fontSize: 16 },
  card: { padding: 22, borderRadius: 16, backgroundColor: '#fff', gap: 14, borderWidth: 1, borderColor: '#dfe6d9' },
  input: { borderWidth: 1, borderColor: '#cbd6c9', borderRadius: 8, padding: 12, color: '#152f2b' },
  button: { backgroundColor: '#204d36', padding: 14, borderRadius: 8, alignItems: 'center', marginTop: 8 },
  buttonText: { color: '#fff', fontWeight: '600', fontSize: 16 }, link: { color: '#316747', textAlign: 'center', padding: 12 },
  error: { backgroundColor: '#fff0ec', padding: 16, color: '#8b2a19', borderRadius: 8 },
  organization: { padding: 20, backgroundColor: '#fff', borderRadius: 12, gap: 6 }, orgTitle: { fontSize: 20, fontWeight: '600', color: '#152f2b' },
});
