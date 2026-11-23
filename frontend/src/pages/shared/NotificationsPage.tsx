import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { PageHeader, Pagination, Tabs } from "@/components/ui/Data";
import { EmptyState, ErrorState, Loading } from "@/components/ui/Feedback";
import { useApi } from "@/hooks/useApi";
import { api } from "@/services/api";
import type { NotificationItem, Page } from "@/types";
import { formatDateTime } from "@/utils/format";

export function NotificationList() {
  const [filter, setFilter] = useState<"all" | "unread">("all");
  const [page, setPage] = useState(1);
  const navigate = useNavigate();
  const { data, setData, loading, error, reload } = useApi<Page<NotificationItem>>("/notifications", { unread_only: filter === "unread", page, page_size: 20 });

  async function open(n: NotificationItem) {
    if (!n.is_read) {
      await api.patch(`/notifications/${n.id}/read`).catch(() => undefined);
      setData((d) => d && { ...d, items: d.items.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)) });
    }
    if (n.link) navigate(n.link);
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <Tabs value={filter} onChange={(v) => { setFilter(v); setPage(1); }} options={[{ value: "all", label: "All" }, { value: "unread", label: "Unread" }]} />
        <Button size="sm" variant="secondary" onClick={async () => { await api.post("/notifications/read-all"); reload(); }}>Mark all as read</Button>
      </div>
      {loading && !data ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data && data.items.length === 0 ? (
        <EmptyState title={filter === "unread" ? "No unread notifications" : "No notifications yet"} icon={<Bell className="h-6 w-6" />}>
          Updates about your account, application and membership will appear here. They are also sent by email and SMS.
        </EmptyState>
      ) : data && (
        <>
          <ul className="border border-line bg-white">
            {data.items.map((n) => (
              <li key={n.id} className="border-b border-line last:border-0">
                <button onClick={() => open(n)} className={`flex w-full gap-3 px-5 py-4 text-left hover:bg-ivory ${n.is_read ? "" : "bg-forest-50/50"}`}>
                  <span className={`mt-2 h-2 w-2 shrink-0 rounded-full ${n.is_read ? "bg-transparent" : "bg-register"}`} aria-label={n.is_read ? undefined : "Unread"} />
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-baseline justify-between gap-2">
                      <span className="font-medium text-ink">{n.title}</span>
                      <span className="text-[13px] text-ink-muted">{formatDateTime(n.created_at)}</span>
                    </span>
                    <span className="mt-0.5 block whitespace-pre-line text-[15px] text-ink-soft">{n.message}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <Pagination page={data.page} pages={data.pages} total={data.total} onPage={setPage} noun="notifications" />
        </>
      )}
    </>
  );
}

export default function NotificationsPage() {
  return (
    <>
      <PageHeader title="Notifications" />
      <NotificationList />
    </>
  );
}
