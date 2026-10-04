import { useEffect } from 'react';
import { router } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import { Loading, Page } from '../src/ui';
export default function CheckoutReturn() { const queries = useQueryClient(); useEffect(() => { void queries.invalidateQueries().then(() => router.replace('/wallet')); }, [queries]); return <Page title="Checking payment"><Loading /></Page>; }
