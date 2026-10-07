import { useEffect, useRef, useState, type ReactNode } from 'react';
import { AccessibilityInfo, ActivityIndicator, Animated, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { remainingSeconds } from '../../packages/api-client/src';

export const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#f7f8f2' }, content: { padding: 22, gap: 20, maxWidth: 800, width: '100%', alignSelf: 'center' },
  title: { fontSize: 32, fontWeight: '800', color: '#183c31', letterSpacing: -1 }, subtitle: { fontSize: 20, fontWeight: '700', color: '#183c31' },
  text: { color: '#334f3d', fontSize: 16, lineHeight: 23 }, muted: { color: '#53655b', fontSize: 14 },
  card: { backgroundColor: '#fff', borderRadius: 20, padding: 20, borderWidth: 1, borderColor: '#d7e2cd', gap: 12 },
  hero: { backgroundColor: '#e4eccf', borderRadius: 24, padding: 26, gap: 15, overflow: 'hidden' },
  input: { backgroundColor: '#fff', borderColor: '#b7c8ad', borderWidth: 1, borderRadius: 9, padding: 13, color: '#183c31', minHeight: 48 },
  button: { backgroundColor: '#244e3b', paddingVertical: 14, paddingHorizontal: 18, borderRadius: 9, alignItems: 'center', minHeight: 48 },
  buttonText: { color: '#fff', fontWeight: '600', fontSize: 16 }, disabled: { opacity: .55 }, error: { backgroundColor: '#fff0ec', color: '#893624', padding: 16, borderRadius: 9 },
  notice: { backgroundColor: '#eaf1d9', color: '#274b2e', padding: 16, borderRadius: 9 }, row: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 }, badge: { fontSize: 12, fontWeight: '700', color: '#47683b' },
  poster: { minHeight: 180, padding: 24, gap: 14, justifyContent: 'space-between', overflow: 'hidden', borderTopLeftRadius: 20, borderTopRightRadius: 20 },
  posterTitle: { fontSize: 40, fontWeight: '800', lineHeight: 42, letterSpacing: -2, color: '#183c31' },
  posterCircle: { position: 'absolute', width: 200, height: 200, borderRadius: 100, borderWidth: 24, borderColor: '#183c3118', right: -65, top: 18 },
});
export function Page({ title, children, onRefresh, refreshing = false }: { title: string; children: ReactNode; onRefresh?: () => void; refreshing?: boolean }) {
  const opacity = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    let active = true;
    void AccessibilityInfo.isReduceMotionEnabled().then(reduced => { if (active && !reduced) { opacity.setValue(0); Animated.timing(opacity, { toValue: 1, duration: 350, useNativeDriver: true }).start(); } }).catch(() => { /* Content remains visible if the OS preference cannot be read. */ });
    const listener = AccessibilityInfo.addEventListener('reduceMotionChanged', reduced => { if (reduced) { opacity.stopAnimation(); opacity.setValue(1); } });
    return () => { active = false; listener.remove(); opacity.stopAnimation(); };
  }, [opacity]);
  return <SafeAreaView style={styles.safe} edges={['bottom', 'left', 'right']}><ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.content} refreshControl={onRefresh ? <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#183c31" /> : undefined}><Text accessibilityRole="header" style={styles.title}>{title}</Text><Animated.View style={{ opacity, gap: 20 }}>{children}</Animated.View></ScrollView></SafeAreaView>;
}
export function Button({ title, onPress, disabled = false }: { title: string; onPress: () => void; disabled?: boolean }) { return <Pressable accessibilityRole="button" accessibilityLabel={title} accessibilityState={{ disabled }} disabled={disabled} onPress={onPress} style={({ pressed }) => [styles.button, disabled && styles.disabled, pressed && { opacity: .8, transform: [{ scale: .98 }] }]}><Text style={styles.buttonText}>{title}</Text></Pressable>; }
export function Input({ label, value, onChangeText, secret = false, keyboard = 'default' }: { label: string; value: string; onChangeText: (value: string) => void; secret?: boolean; keyboard?: 'default' | 'email-address' | 'number-pad' }) { return <View style={{ gap: 7 }}><Text style={styles.text}>{label}</Text><TextInput accessibilityLabel={label} value={value} onChangeText={onChangeText} secureTextEntry={secret} autoCapitalize="none" keyboardType={keyboard} style={styles.input} /></View>; }
export function Alert({ error }: { error: unknown }) { return error ? <Text accessibilityRole="alert" style={styles.error}>{error instanceof Error ? error.message : String(error)}</Text> : null; }
export function Loading() { return <ActivityIndicator accessibilityLabel="Loading" color="#244e3b" />; }
export function SignInPrompt() { return <View style={styles.card}><Text style={styles.text}>Sign in to view your tickets and reserve a place.</Text><Button title="Open my account" onPress={() => router.push('/account')} /></View>; }
export function Countdown({ expiresAt }: { expiresAt: string }) { const [now, setNow] = useState(Date.now()); useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []); const value = remainingSeconds(expiresAt, now); return <Text accessibilityRole="timer" style={styles.notice}>{value ? `Held for ${Math.floor(value / 60)}:${String(value % 60).padStart(2, '0')}` : 'Hold expired. Choose tickets again.'}</Text>; }
