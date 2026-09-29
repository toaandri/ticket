import { View, Text, StyleSheet } from 'react-native'
import { StatusBar } from 'expo-status-bar'

export default function RootLayout() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Ticket</Text>
      <Text style={styles.subtitle}>Event management platform</Text>
      <Text style={styles.phase}>Phase 0 — scaffold</Text>
      <StatusBar style="auto" />
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#475569',
    marginBottom: 4,
  },
  phase: {
    fontSize: 12,
    color: '#94a3b8',
  },
})
