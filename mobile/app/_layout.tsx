import { Tabs } from 'expo-router';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StatusBar } from 'expo-status-bar';
import { SessionProvider } from '../src/session';
import { Text } from 'react-native';
const queries = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 10000 } } });
export default function Layout() {
  return <SafeAreaProvider><QueryClientProvider client={queries}><SessionProvider><StatusBar style="dark" /><Tabs screenOptions={{ headerStyle: { backgroundColor: '#f8f9f4' }, headerTintColor: '#183c31', tabBarActiveTintColor: '#244e3b', tabBarStyle: { backgroundColor: '#f8f9f4' }, tabBarLabelStyle: { fontSize: 11 } }}>
    <Tabs.Screen name="index" options={{ title: 'Discover', tabBarIcon: () => <Text>◉</Text> }} /><Tabs.Screen name="wallet" options={{ title: 'My tickets', tabBarIcon: () => <Text>▤</Text> }} /><Tabs.Screen name="account" options={{ title: 'Account', tabBarIcon: () => <Text>◎</Text> }} /><Tabs.Screen name="scanner" options={{ title: 'Scanner', tabBarIcon: () => <Text>▣</Text> }} /><Tabs.Screen name="events/[id]" options={{ href: null, title: 'Event details' }} /><Tabs.Screen name="checkout-return" options={{ href: null, title: 'Payment return' }} />
  </Tabs></SessionProvider></QueryClientProvider></SafeAreaProvider>;
}
