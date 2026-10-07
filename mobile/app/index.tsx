import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { router } from 'expo-router';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import type { Paginated, TicketEvent } from '../../packages/api-client/src';
import { money } from '../../packages/api-client/src';
import { useSession } from '../src/session';
import { Alert, Button, Input, Loading, Page, styles } from '../src/ui';

export default function Discover() {
  const { api } = useSession(); const [search, setSearch] = useState(''); const [category, setCategory] = useState(''); const [page, setPage] = useState(1);
  const query = new URLSearchParams({ search, category, page: String(page), ordering: 'start_at' });
  const events = useQuery({ queryKey: ['events', query.toString()], queryFn: () => api<Paginated<TicketEvent>>(`/events/?${query}`), placeholderData: keepPreviousData });
  return <Page title="Your next good moment." onRefresh={() => void events.refetch()} refreshing={events.isRefetching}>
    <View style={[styles.hero, { backgroundColor: '#183c31' }]}><View accessible={false} style={[styles.posterCircle, { borderColor: '#d9ef9b22', right: -55, top: -40 }]} /><Text style={[styles.badge, { color: '#d9ef9b', letterSpacing: 2 }]}>GO WHERE THE GOOD THINGS ARE</Text><Text style={[styles.title, { fontSize: 42, color: '#f4f5e9', lineHeight: 46 }]}>Life happens{ '\n' }when you{ '\n' }show up.</Text><Text style={[styles.text, { color: '#d0dfc4' }]}>Small stages. Big ideas. A fresh reason to leave the house.</Text><Text style={[styles.muted, { color: '#d9ef9b' }]}>Synthetic events · Simulated transactions</Text></View>
    <Input label="Search events" value={search} onChangeText={value => { setSearch(value); setPage(1); }} />
    <View style={styles.row}>{['', 'Music', 'Theatre', 'Technology'].map(value => <Pressable key={value} accessibilityRole="button" accessibilityState={{ selected: category === value }} style={({ pressed }) => [{ paddingVertical: 11, paddingHorizontal: 16, minHeight: 44, borderRadius: 24, borderWidth: 1, borderColor: '#d7e2cd', backgroundColor: category === value ? '#183c31' : '#fff', opacity: pressed ? .7 : 1 }]} onPress={() => { setCategory(value); setPage(1); }}><Text style={[styles.muted, { color: category === value ? '#fff' : '#183c31', fontWeight: '600' }]}>{value || 'All experiences'}</Text></Pressable>)}</View>
    <View style={[styles.row, { justifyContent: 'space-between' }]}><Text accessibilityRole="header" style={styles.subtitle}>Worth being there.</Text><Text style={styles.muted}>{events.data?.count ?? '…'} events</Text></View><Alert error={events.error} />{events.isPending && <Loading />}
    {events.data?.results.map(event => <Pressable key={event.id} accessibilityRole="button" accessibilityLabel={`View ${event.title}`} style={({ pressed }) => [styles.card, { padding: 0, gap: 0, opacity: pressed ? .86 : 1 }]} onPress={() => router.push(`/events/${event.id}`)}>
      <View accessible={false} style={[styles.poster, { backgroundColor: event.category === 'Theatre' ? '#edc8ab' : event.category === 'Technology' ? '#cacdee' : '#d9e8b4' }]}><View style={styles.posterCircle} /><Text style={styles.badge}>{(event.category || 'Experience').toUpperCase()} / TICKET</Text><Text style={styles.posterTitle}>{event.category === 'Theatre' ? 'Take the stage.' : event.category === 'Technology' ? 'Ideas. In motion.' : 'Feel everything.'}</Text></View>
      <View style={{ padding: 22, gap: 10 }}><Text style={styles.muted}>{new Intl.DateTimeFormat('en', { dateStyle: 'medium', timeStyle: 'short', timeZone: event.event_timezone }).format(new Date(event.start_at))}</Text><Text style={styles.subtitle}>{event.title}</Text><Text style={styles.muted}>{event.venue_name} · {event.city}</Text><View style={[styles.row, { borderTopWidth: 1, borderColor: '#d7e2cd', paddingTop: 14, justifyContent: 'space-between' }]}><Text style={[styles.text, { fontWeight: '700' }]}>{event.ticket_types.length ? `From ${money(Math.min(...event.ticket_types.map(type => type.price_minor)), event.ticket_types[0].currency)}` : 'Details soon'}</Text><Text style={styles.badge}>SEE TICKETS ↗</Text></View></View>
    </Pressable>)}
    {events.data && !events.data.results.length && <View style={styles.card}><Text style={styles.subtitle}>A little further afield?</Text><Text style={styles.muted}>No events found. Try another search or category.</Text><Button title="Reset filters" onPress={() => { setSearch(''); setCategory(''); setPage(1); }} /></View>}
    <View style={styles.row}>{events.data?.previous && <Button title="Previous events" disabled={events.isPlaceholderData} onPress={() => setPage(page - 1)} />}{events.data?.next && <Button title="More events" disabled={events.isPlaceholderData} onPress={() => setPage(page + 1)} />}</View>
  </Page>;
}
