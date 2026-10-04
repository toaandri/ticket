import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { Audit, Paginated, components } from '../../packages/api-client/src';
import { post } from '../../packages/api-client/src';
import { useSession } from './session';
import { Alert, Empty, Field, Form, humanDate } from './ui';

type DeadLetter = components['schemas']['DeadLetter'];
export default function Admin() {
  const { user, api } = useSession(); const queries = useQueryClient(); const [busy, setBusy] = useState(false); const [error, setError] = useState<unknown>(null); const [notice, setNotice] = useState('');
  const audit = useQuery({ queryKey: ['platform-audit', user?.id], queryFn: () => api<Paginated<Audit>>('/admin/audit/'), enabled: !!user?.is_superuser });
  const failures = useQuery({ queryKey: ['dead-letters', user?.id], queryFn: () => api<Paginated<DeadLetter>>('/admin/outbox/'), enabled: !!user?.is_superuser });
  async function action(callback: () => Promise<unknown>) { setBusy(true); setError(null); try { await callback(); setNotice('Action recorded in the platform audit.'); await queries.invalidateQueries(); } catch (err) { setError(err); } finally { setBusy(false); } }
  if (!user?.is_superuser) return <Empty>Platform administrator access required.</Empty>;
  return <><p className="eyebrow">Platform operations</p><h1>Moderation & recovery</h1><Alert error={error ?? audit.error ?? failures.error} />{notice && <p role="status" className="notice">{notice}</p>}<div className="dashboard-grid"><section className="panel"><Form title="Moderate organization" busy={busy} onSubmit={data => action(() => api(`/admin/organizations/${data.get('organization_id')}/moderate/`, post({ reason: data.get('reason'), suspended: data.get('action') === 'suspend' })))}><Field label="Organization UUID" name="organization_id" /><label>Action<select name="action"><option value="suspend">Suspend ticket sales</option><option value="restore">Restore organization</option></select></label><Field label="Moderation reason" name="reason" /></Form><Form title="Cancel event through moderation" busy={busy} onSubmit={data => action(() => api(`/admin/events/${data.get('event_id')}/moderate/`, post({ reason: data.get('event_reason') })))}><Field label="Event UUID" name="event_id" /><Field label="Cancellation reason" name="event_reason" /></Form></section><section><h2>Undelivered messages</h2>{failures.data?.results.map(message => <article className="notification" key={message.id}><h3>{message.event_type}</h3><p>{message.attempts} attempts · {message.aggregate_id}</p><button disabled={busy} onClick={() => void action(() => api(`/admin/outbox/${message.id}/replay/`, post({})))}>Retry delivery</button></article>)}{failures.data && !failures.data.results.length && <Empty>No failed messages.</Empty>}</section></div><section><h2>Platform audit</h2><div className="table-scroll"><table><thead><tr><th>Time</th><th>Action</th><th>Resource</th></tr></thead><tbody>{audit.data?.results.map(entry => <tr key={entry.id}><td>{humanDate(entry.created_at)}</td><td>{entry.action}</td><td>{entry.entity_type} {entry.entity_id}</td></tr>)}</tbody></table></div></section></>;
}
