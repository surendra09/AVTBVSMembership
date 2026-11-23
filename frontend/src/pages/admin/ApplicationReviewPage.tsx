import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { CheckCircle2, CircleAlert, Pencil, XCircle } from "lucide-react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { PageHeader, Panel, RegisterRows } from "@/components/ui/Data";
import { Alert, ErrorState, Loading, StatusBadge } from "@/components/ui/Feedback";
import { TextAreaField, TextField } from "@/components/ui/Form";
import { Modal } from "@/components/ui/Modal";
import { DeclarationText, DocumentGallery, FormDataView, HistoryTimeline } from "@/features/registration/ApplicationView";
import { useApi } from "@/hooks/useApi";
import { usePublicConfig } from "@/hooks/usePublicConfig";
import { api, parseApiError } from "@/services/api";
import type { AdminApplication, OfficeUse } from "@/types";
import { formatDate, formatDateTime } from "@/utils/format";
import { today } from "@/features/registration/formModel";

type Action = "approve" | "corrections" | "reject" | null;

export default function ApplicationReviewPage() {
  const { id } = useParams();
  const { data: app, setData, loading, error, reload } = useApi<AdminApplication>(`/admin/applications/${id}`);
  const { organisation } = usePublicConfig();
  const [action, setAction] = useState<Action>(null);

  if (loading && !app) return <Loading label="Loading application" />;
  if (error || !app) return <ErrorState message={error ?? "Not found"} onRetry={reload} />;
  const reviewable = app.status === "PENDING" || app.status === "RESUBMITTED";
  const ic = app.introducer_check;

  return (
    <>
      <Link to="/admin/applications/pending" className="mb-3 inline-block text-[15px] text-forest underline decoration-forest/30">Back to applications</Link>
      <PageHeader title={app.full_name || "Application"}
        description={<>Application no. {app.application_number}. Submitted {formatDateTime(app.last_submitted_at)}{app.history.filter((h) => h.action === "RESUBMITTED").length ? " (resubmitted)" : ""}.</>}
        actions={<StatusBadge status={app.status} />} />

      {app.status === "APPROVED" && app.membership_number && (
        <div className="mb-5"><Alert tone="success" title={`Approved. Membership no. ${app.membership_number}`}
          action={app.member_id && <ButtonLink size="sm" variant="secondary" to={`/admin/members/${app.member_id}`}>Open member record</ButtonLink>} /></div>
      )}
      {app.status === "REJECTED" && <div className="mb-5"><Alert tone="error" title="Rejected">{app.rejection_reason}</Alert></div>}
      {app.status === "CORRECTION_REQUIRED" && <div className="mb-5"><Alert tone="warning" title="Waiting for the applicant's corrections">{app.correction_notes}</Alert></div>}

      <div className="grid gap-6 xl:grid-cols-[1fr_22rem]">
        <div className="space-y-6">
          <FormDataView data={app} aadhaar={app.aadhaar_number} />
          <Panel title="Photographs and documents"><DocumentGallery documents={app.documents} /></Panel>
          <Panel title="Declaration">
            <DeclarationText name={app.full_name} father={app.father_name} community={organisation.community_name} />
            <p className="mt-3 text-[15px] text-ink-soft">
              {app.declaration_accepted ? "Confirmed by the applicant." : "Not confirmed."} Place: {app.declaration_place || "—"}. Date: {app.declaration_date ? formatDate(app.declaration_date) : "—"}.
            </p>
          </Panel>
        </div>

        <aside className="space-y-6">
          {reviewable && (
            <Panel title="Decision">
              <div className="grid gap-2">
                <Button onClick={() => setAction("approve")}><CheckCircle2 className="h-4 w-4" /> Approve</Button>
                <Button variant="secondary" onClick={() => setAction("corrections")}><Pencil className="h-4 w-4" /> Request corrections</Button>
                <Button variant="quiet" className="text-danger hover:text-danger" onClick={() => setAction("reject")}><XCircle className="h-4 w-4" /> Reject</Button>
              </div>
            </Panel>
          )}
          <Panel title="Checks">
            <ul className="space-y-3 text-[15px]">
              <Check ok={ic.registration_number_found}
                label={ic.registration_number_found ? `Introducer no. ${app.introducer_reg_no} belongs to ${ic.member_name}` : `No member with no. ${app.introducer_reg_no || "—"} in the register`}
                detail={ic.registration_number_found ? (ic.member_status !== "ACTIVE" ? "That membership is inactive." : ic.phone_matches === false ? "The phone number given doesn't match that member's records." : ic.phone_matches ? "Phone number matches." : undefined) : "The introducer may be a paper member not yet entered online."} />
              <Check ok={(app.age_years ?? 0) >= 18} label={`Age ${app.age_years ?? "unknown"} years`} />
              <Check ok={app.duplicate_aadhaar_member_numbers.length === 0}
                label={app.duplicate_aadhaar_member_numbers.length ? `Aadhaar already used by member no. ${app.duplicate_aadhaar_member_numbers.join(", ")}` : app.aadhaar_number ? "Aadhaar not used by another member" : "No Aadhaar number given"} />
              <Check ok={app.declaration_accepted} label="Declaration confirmed" />
            </ul>
          </Panel>
          <Panel title="Applicant's account">
            <div className="register">
              <RegisterRows rows={[
                { label: "Name", value: app.applicant_account_name }, { label: "Email", value: app.applicant_account_email },
                { label: "Mobile", value: app.applicant_account_phone },
              ]} />
            </div>
          </Panel>
          <Panel title="History"><HistoryTimeline history={app.history} /></Panel>
        </aside>
      </div>

      <ApproveModal open={action === "approve"} app={app} onClose={() => setAction(null)} onDone={(a) => { setData(a); setAction(null); }} />
      <ReasonModal open={action === "corrections"} app={app} kind="corrections" onClose={() => setAction(null)} onDone={(a) => { setData(a); setAction(null); }} />
      <ReasonModal open={action === "reject"} app={app} kind="reject" onClose={() => setAction(null)} onDone={(a) => { setData(a); setAction(null); }} />
    </>
  );
}

function Check({ ok, label, detail }: { ok: boolean; label: string; detail?: string }) {
  return (
    <li className="flex gap-2">
      {ok ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-ok" /> : <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-caution" />}
      <span>{label}{detail && <span className="block text-sm text-ink-muted">{detail}</span>}</span>
    </li>
  );
}

function ApproveModal({ open, app, onClose, onDone }: { open: boolean; app: AdminApplication; onClose: () => void; onDone: (a: AdminApplication) => void }) {
  const [err, setErr] = useState<string | null>(null);
  const { register, handleSubmit, formState: { isSubmitting } } = useForm<OfficeUse & { note: string }>({
    defaultValues: { receipt_date: today() },
  });
  const submit = handleSubmit(async (values) => {
    setErr(null);
    const body = Object.fromEntries(Object.entries(values).map(([k, v]) => [k, v === "" ? null : v]));
    try {
      const { data } = await api.post<AdminApplication>(`/admin/applications/${app.id}/approve`, body);
      onDone(data);
    } catch (e) {
      setErr(parseApiError(e).message);
    }
  });
  return (
    <Modal open={open} onClose={onClose} title={`Approve ${app.full_name}?`} wide footer={<>
      <Button variant="quiet" onClick={onClose}>Cancel</Button>
      <Button onClick={submit} loading={isSubmitting}>Approve and assign number</Button>
    </>}>
      <form onSubmit={submit} className="space-y-4">
        <p className="text-[15px] text-ink-soft">
          Approving creates the official member record and assigns the next membership number. The applicant is notified by SMS, email and on the website. This can't be undone from here.
        </p>
        {err && <Alert tone="error">{err}</Alert>}
        <p className="font-display text-forest">For office use</p>
        <div className="grid gap-3 sm:grid-cols-3">
          <TextField label="Verified by" {...register("verified_by")} />
          <TextField label="Rec. No." {...register("receipt_number")} />
          <TextField label="Date" type="date" {...register("receipt_date")} />
        </div>
        <p className="text-sm text-ink-soft">Membership Enrollment Committee</p>
        <div className="grid gap-3 sm:grid-cols-3">
          <TextField label="Chairman" {...register("committee_chairman")} />
          <TextField label="Secretary" {...register("committee_secretary")} />
          <TextField label="President" {...register("committee_president")} />
        </div>
        <TextAreaField label="Note (optional)" rows={2} {...register("note")} />
      </form>
    </Modal>
  );
}

function ReasonModal({ open, app, kind, onClose, onDone }: { open: boolean; app: AdminApplication; kind: "corrections" | "reject"; onClose: () => void; onDone: (a: AdminApplication) => void }) {
  const [text, setText] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const min = kind === "corrections" ? 10 : 5;
  async function submit() {
    if (text.trim().length < min) return setErr(kind === "corrections" ? "Describe each correction needed (at least 10 characters)." : "Give the reason (at least 5 characters).");
    setBusy(true);
    setErr(null);
    try {
      const { data } = await api.post<AdminApplication>(`/admin/applications/${app.id}/${kind}`, kind === "corrections" ? { notes: text } : { reason: text });
      setText("");
      onDone(data);
    } catch (e) {
      setErr(parseApiError(e).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal open={open} onClose={onClose} title={kind === "corrections" ? "Request corrections" : "Reject this application?"} footer={<>
      <Button variant="quiet" onClick={onClose}>Cancel</Button>
      <Button variant={kind === "reject" ? "danger" : "primary"} onClick={submit} loading={busy}>{kind === "corrections" ? "Send correction request" : "Reject application"}</Button>
    </>}>
      <div className="space-y-3">
        <p className="text-[15px] text-ink-soft">
          {kind === "corrections"
            ? "The applicant will be able to edit and resubmit. List exactly what is wrong so they can fix it in one go."
            : "Rejection is final for this application and is different from asking for corrections. The applicant will see the reason."}
        </p>
        <TextAreaField label={kind === "corrections" ? "Corrections needed" : "Reason for rejection"} rows={5} value={text}
          onChange={(e) => setText(e.target.value)} error={err ?? undefined}
          placeholder={kind === "corrections" ? "e.g. Father's name differs from the identity proof. Please upload a clearer photograph." : ""} />
      </div>
    </Modal>
  );
}
