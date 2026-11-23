import { Link, useNavigate } from "react-router-dom";
import { Avatar, PageHeader, Panel } from "@/components/ui/Data";
import { Alert, ErrorState, Loading, StatusBadge } from "@/components/ui/Feedback";
import { useApi } from "@/hooks/useApi";
import type { ApplicationListItem } from "@/types";
import { formatDate } from "@/utils/format";

interface Stats {
  total_members: number;
  active_members: number;
  pending_applications: number;
  correction_requests: number;
  rejected_applications: number;
  approved_applications: number;
  new_members_30d: number;
  pending_edit_requests: number;
  failed_deliveries: number;
  awaiting_review: ApplicationListItem[];
}

export function StatStrip({ items }: { items: { label: string; value: number; to?: string; emphasis?: boolean }[] }) {
  return (
    <dl className="grid grid-cols-2 border border-line bg-white sm:grid-cols-3 lg:grid-cols-6">
      {items.map((s) => {
        const body = (
          <>
            <dt className="text-sm text-ink-soft">{s.label}</dt>
            <dd className={`mt-1 font-display text-3xl ${s.emphasis && s.value > 0 ? "text-register" : "text-forest"}`}>{s.value.toLocaleString("en-IN")}</dd>
          </>
        );
        return (
          <div key={s.label} className="border-b border-r border-line px-4 py-4 last:border-r-0 lg:border-b-0">
            {s.to ? <Link to={s.to} className="block hover:opacity-80">{body}</Link> : body}
          </div>
        );
      })}
    </dl>
  );
}

export default function AdminDashboard() {
  const { data, loading, error, reload } = useApi<Stats>("/admin/dashboard");
  const navigate = useNavigate();
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? ""} onRetry={reload} />;
  return (
    <>
      <PageHeader title="Membership administration" description="Applications waiting for verification, and the state of the register." />
      <StatStrip items={[
        { label: "Total members", value: data.total_members, to: "/admin/members" },
        { label: "Active members", value: data.active_members, to: "/admin/members?status=ACTIVE" },
        { label: "Pending applications", value: data.pending_applications, to: "/admin/applications/pending", emphasis: true },
        { label: "Correction requests", value: data.correction_requests, to: "/admin/applications/corrections" },
        { label: "Rejected applications", value: data.rejected_applications, to: "/admin/applications/rejected" },
        { label: "New members (30 days)", value: data.new_members_30d, to: "/admin/members?sort=recent" },
      ]} />
      <div className="mt-6 space-y-3">
        {data.pending_edit_requests > 0 && (
          <Alert tone="warning" title={`${data.pending_edit_requests} profile edit request${data.pending_edit_requests > 1 ? "s" : ""} waiting`}
            action={<Link className="text-sm font-medium underline" to="/admin/edit-requests">Review</Link>} />
        )}
        {data.failed_deliveries > 0 && (
          <Alert tone="error" title={`${data.failed_deliveries} email/SMS message${data.failed_deliveries > 1 ? "s" : ""} could not be delivered`}
            action={<Link className="text-sm font-medium underline" to="/admin/notifications?tab=deliveries">See details</Link>} />
        )}
      </div>
      <Panel className="mt-6" title="Oldest applications awaiting verification"
        action={<Link to="/admin/applications/pending" className="text-[15px] text-forest underline decoration-forest/30">All pending</Link>}>
        {data.awaiting_review.length === 0 ? <p className="text-ink-soft">Nothing is waiting. New submissions will appear here.</p> : (
          <ul className="divide-y divide-line">
            {data.awaiting_review.map((a) => (
              <li key={a.id}>
                <button onClick={() => navigate(`/admin/applications/${a.id}`)} className="flex w-full items-center gap-3 py-3 text-left hover:bg-ivory">
                  <Avatar src={a.photo_url} name={a.full_name ?? "?"} size={40} />
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium">{a.full_name}</span>
                    <span className="block text-sm text-ink-muted">{a.application_number}, {a.city}</span>
                  </span>
                  <span className="hidden text-sm text-ink-muted sm:block">Submitted {formatDate(a.last_submitted_at)}</span>
                  <StatusBadge status={a.status} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </>
  );
}
