import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { router } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import type { Paginated, TicketEvent } from '../../packages/api-client/src';
import { money } from '../../packages/api-client/src';
import { useSession } from '../src/session';
import { Alert, Button, Input, Loading, Page, styles } from '../src/ui';

export default function Discover() {
  const { api } = useSession(); const [search, setSearch] = useState(''); const [category, setCategory] = useState(''); const [page, setPage] = useState(1);
  const query = new URLSearchParams({ search, category, page: String(page) });
  const events = useQuery({ queryKey: ['events', query.toString()], queryFn: () => api<Paginated<TicketEvent>>(`/events/?${query}`) });
  return <Page title="Find your next good moment."><View style={styles.hero}><Text style={styles.badge}>GOOD MOMENTS START HERE</Text><Text style={styles.subtitle}>Small stages. Big ideas.</Text><Text style={styles.text}>Find your people, and an event worth being there for.</Text><Text style={styles.muted}>Synthetic events · All payments are simulated.</Text></View><Input label="Search events" value={search} onChangeText={value => { setSearch(value); setPage(1); }} /><View style={styles.row}>{['', 'Music', 'Theatre', 'Technology'].map(value => <Pressable key={value} accessibilityRole="button" accessibilityState={{ selected: category === value }} style={[styles.card, { padding: 10, backgroundColor: category === value ? '#dce8c7' : '#fff' }]} onPress={() => { setCategory(value); setPage(1); }}><Text style={styles.text}>{value || 'All'}</Text></Pressable>)}</View><Alert error={events.error} />{events.isPending && <Loading />}{events.data?.results.map(event => <Pressable key={event.id} accessibilityRole="button" accessibilityLabel={`View ${event.title}`} style={styles.card} onPress={() => router.push(`/events/${event.id}`)}><Text style={styles.badge}>{event.category} · {event.status}</Text><Text style={styles.subtitle}>{event.title}</Text><Text style={styles.muted}>{new Date(event.start_at).toLocaleString()} · {event.venue_name}</Text><Text style={styles.text}>{event.ticket_types.length ? `From ${money(Math.min(...event.ticket_types.map(type => type.price_minor)), event.ticket_types[0].currency)}` : 'Ticket information coming soon'} ↗</Text></Pressable>)}{events.data && !events.data.results.length && <Text style={styles.muted}>No events found. Try another search.</Text>}{events.data?.previous && <Button title="Previous events" onPress={() => setPage(page - 1)} />}{events.data?.next && <Button title="More events" onPress={() => setPage(page + 1)} />}</Page>;
}
