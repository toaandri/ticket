import { Redirect } from 'expo-router'

// Entry point — redirect to the home screen
export default function Index() {
  return <Redirect href="/(tabs)" />
}
