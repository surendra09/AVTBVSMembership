import { useState } from "react";
import { Link } from "react-router-dom";
import { ClipboardList } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { PageHeader, Pagination, Tabs } from "@/components/ui/Data";
import { Alert, EmptyState, ErrorState, Loading, StatusBadge } from "@/components/ui/Feedback";
import { TextAreaField } from "@/components/ui/Form";
import { Modal } from "@/components/ui/Modal";
import { useApi } from "@/hooks/useApi";
import { usePublicConfig } from "@/hooks/usePublicConfig";
import { api, parseApiError } from "@/services/api";
import type { EditRequest, EditRequestStatus, Page } from "@/types";
import { formatDateTime, timeRemaining } from "@/utils/format";

type Decision = { req: EditRequest; kind: "approve" | "reject" | "revoke" } | null;

export default function EditRequestsPage() {
  const [tab, setTab] = useState<EditRequestStatus | "ALL">("PENDING");
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useApi<Page<EditRequest>>("/admin/edit-requests", { status: tab === "ALL" ? undefined : tab, page });
  const [decision, setDecision] = useState<Decision>(null);
  const [note, setNote] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { form } = usePublicConfig();

  async function decide() {
    if (!decision) return;
    if (decision.kind === "reject" && note.trim().length < 5) return setErr("Tell the member why (at least 5 characters).");
    setBusy(true);
    setErr(null);
    try {
      await api.post(`/admin/edit-requests/${decision.req.id}/${decision.kind}`, decision.kind === "revoke" ? undefined : { note: note || null });
      setDecision(null);
      setNote("");
      reload();
    } catch (e) { setErr(parseApiError(e).message); } finally { setBusy(false); }
  }

  const titles = { approve: "Allow this member to edit?", reject: "Decline this request?", revoke: "End editing access now?" };
  return (
    <>
      <PageHeader title="Profile edit requests" description={`Approved members ask here to change their locked details. Approving opens a ${form.edit_permission_hours}-hour editing window.`} />
      <Tabs value={tab} onChange={(v) => { setTab(v); setPage(1); }} options={[
        { value: "PENDING", label: "Waiting" }, { value: "APPROVED", label: "Approved" }, { value: "REJECTED", label: "Declined" }, { value: "ALL", label: "All" }]} />
      <div className="mt-4">
        {loading && !data ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data && data.items.length === 0 ? (
          <EmptyState title={tab === "PENDING" ? "No requests waiting" : "No requests"} icon={<ClipboardList className="h-6 w-6" />}>
            Requests appear here when a member asks to change their details.
          </EmptyState>
        ) : data && (
          <>
            <ul className="space-y-3">
              {data.items.map((r) => (
                <li key={r.id} className="border border-line bg-white p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <Link to={`/admin/members/${r.member_id}`} className="font-medium text-forest hover:underline">{r.member_name}</Link>
                      <span className="ml-2 text-sm text-register">No. {r.membership_number}</span>
                      <p className="text-[13px] text-ink-muted">Requested {formatDateTime(r.created_at)}</p>
                    </div>
                    <StatusBadge status={r.status} label={r.status === "APPROVED" ? (r.permission_active ? "Editing open" : "Window closed") : r.status === "REJECTED" ? "Declined" : "Waiting"} />
                  </div>
                  <p className="mt-2 whitespace-pre-line text-[15px] text-ink">{r.reason}</p>
                  {r.review_note && <p className="mt-2 text-sm text-ink-soft">Note: {r.review_note}</p>}
                  {r.status === "APPROVED" && r.permission_expires_at && (
                    <p className="mt-2 text-sm text-ink-soft">Window {formatDateTime(r.permission_starts_at)} to {formatDateTime(r.permission_expires_at)}{r.permission_active ? `, ${timeRemaining(r.permission_expires_at)}` : ""}. Approved by {r.reviewed_by_name}.</p>
                  )}
                  <div className="mt-3 flex flex-wrap gap-2">
                    {r.status === "PENDING" && <>
                      <Button size="sm" onClick={() => setDecision({ req: r, kind: "approve" })}>Approve for {form.edit_permission_hours} hours</Button>
                      <Button size="sm" variant="secondary" onClick={() => setDecision({ req: r, kind: "reject" })}>Decline</Button>
                    </>}
                    {r.permission_active && <Button size="sm" variant="quiet" onClick={() => setDecision({ req: r, kind: "revoke" })}>End access now</Button>}
                  </div>
                </li>
              ))}
            </ul>
            <Pagination page={data.page} pages={data.pages} total={data.total} onPage={setPage} noun="requests" />
          </>
        )}
      </div>
      <Modal open={!!decision} onClose={() => setDecision(null)} title={decision ? titles[decision.kind] : ""} footer={<>
        <Button variant="quiet" onClick={() => setDecision(null)}>Cancel</Button>
        <Button variant={decision?.kind === "approve" ? "primary" : "danger"} loading={busy} onClick={decide}>
          {decision?.kind === "approve" ? "Approve" : decision?.kind === "reject" ? "Decline request" : "End access"}
        </Button>
      </>}>
        {decision && (
          <div className="space-y-3">
            {decision.kind === "approve" && <Alert tone="info">{decision.req.member_name} will be able to edit their details for exactly {form.edit_permission_hours} hours from now. Access closes automatically.</Alert>}
            {decision.kind === "revoke" && <p className="text-ink-soft">The member will no longer be able to save changes.</p>}
            {decision.kind !== "revoke" && <TextAreaField label={decision.kind === "reject" ? "Reason for declining" : "Note to the member (optional)"} rows={3}
              value={note} onChange={(e) => setNote(e.target.value)} error={err ?? undefined} />}
            {decision.kind === "revoke" && err && <Alert tone="error">{err}</Alert>}
          </div>
        )}
      </Modal>
    </>
  );
}
