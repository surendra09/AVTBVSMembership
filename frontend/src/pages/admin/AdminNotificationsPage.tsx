import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { PageHeader, Pagination, SearchInput, Table, Tabs } from "@/components/ui/Data";
import { ErrorState, Loading, StatusBadge } from "@/components/ui/Feedback";
import { SelectField } from "@/components/ui/Form";
import { useApi, useDebounced } from "@/hooks/useApi";
import { api } from "@/services/api";
import { NotificationList } from "@/pages/shared/NotificationsPage";
import { formatDateTime } from "@/utils/format";

interface Delivery {
  id: number; event: string; channel: "EMAIL" | "SMS"; recipient: string; subject: string | null; body_preview: string;
  status: string; attempts: number; last_error: string | null; sent_at: string | null; created_at: string;
}

function Deliveries() {
  const [status, setStatus] = useState("");
  const [channel, setChannel] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const dq = useDebounced(q);
  const { data, loading, error, reload } = useApi<{ items: Delivery[]; total: number; page: number; pages: number }>(
    "/admin/notification-deliveries", { status: status || undefined, channel: channel || undefined, q: dq || undefined, page });
  return (
    <>
      <div className="my-4 grid gap-3 sm:grid-cols-[1fr_10rem_10rem]">
        <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Recipient or event" />
        <SelectField label="Status" wrapperClassName="[&>label]:sr-only" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          options={[{ value: "", label: "Any status" }, { value: "SENT", label: "Sent" }, { value: "PENDING", label: "Queued" }, { value: "FAILED", label: "Failed" }]} />
        <SelectField label="Channel" wrapperClassName="[&>label]:sr-only" value={channel} onChange={(e) => { setChannel(e.target.value); setPage(1); }}
          options={[{ value: "", label: "Email and SMS" }, { value: "EMAIL", label: "Email" }, { value: "SMS", label: "SMS" }]} />
      </div>
      {loading && !data ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data && (
        <>
          <Table caption="Delivery records" rows={data.items} rowKey={(r) => r.id} columns={[
            { key: "w", header: "Queued", render: (r) => <span className="text-sm">{formatDateTime(r.created_at)}</span> },
            { key: "c", header: "Channel", render: (r) => r.channel === "EMAIL" ? "Email" : "SMS" },
            { key: "r", header: "To", render: (r) => <span className="text-sm">{r.recipient}</span> },
            { key: "m", header: "Message", render: (r) => <span className="line-clamp-2 text-sm text-ink-soft">{r.subject ?? r.body_preview}</span> },
            { key: "s", header: "Status", render: (r) => (
              <span>
                <StatusBadge status={r.status === "PENDING" ? "PENDING" : r.status} label={r.status === "PENDING" ? "Queued" : undefined} />
                {r.attempts > 1 && <span className="ml-1 text-[12px] text-ink-muted">{r.attempts} tries</span>}
                {r.last_error && <span className="mt-1 block max-w-xs truncate text-[12px] text-danger" title={r.last_error}>{r.last_error}</span>}
              </span>) },
            { key: "a", header: "", render: (r) => r.status === "FAILED" && !r.body_preview.startsWith("[sensitive") ? (
              <Button size="sm" variant="secondary" onClick={async () => { await api.post(`/admin/notification-deliveries/${r.id}/retry`); reload(); }}>Retry</Button>) : null },
          ]} />
          <Pagination page={data.page} pages={data.pages} total={data.total} onPage={setPage} noun="messages" />
        </>
      )}
    </>
  );
}

export default function AdminNotificationsPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") === "deliveries" ? "deliveries" : "mine";
  return (
    <>
      <PageHeader title="Notifications" description="Your own notifications, and the record of every email and SMS the system has sent." />
      <Tabs value={tab} onChange={(v) => setParams(v === "mine" ? {} : { tab: v })} options={[{ value: "mine", label: "My notifications" }, { value: "deliveries", label: "Email and SMS records" }]} />
      <div className="mt-4">{tab === "mine" ? <NotificationList /> : <Deliveries />}</div>
    </>
  );
}
