import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Pencil, Printer } from "lucide-react";
import { FileUpload } from "@/components/FileUpload";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Avatar, Panel, RegisterRows, Table } from "@/components/ui/Data";
import { Alert, ErrorState, Loading, StatusBadge } from "@/components/ui/Feedback";
import { TextAreaField, TextField } from "@/components/ui/Form";
import { Modal } from "@/components/ui/Modal";
import { OfficeUseFields, officePayload, OFFICE_KEYS, type OfficeValues } from "@/features/admin/OfficeUseFields";
import { FormDataView } from "@/features/registration/ApplicationView";
import { FormSection, MembershipFormFields } from "@/features/registration/MembershipFormFields";
import { profileSchema, toFormValues, toPayload, type FormValues, formResolver } from "@/features/registration/formModel";
import { useApi } from "@/hooks/useApi";
import { usePublicConfig } from "@/hooks/usePublicConfig";
import { api, parseApiError } from "@/services/api";
import type { AdminMember, DocumentType } from "@/types";
import { formatDate, formatDateTime, fieldLabel } from "@/utils/format";

const DOC_TYPES: { type: DocumentType; accept: "image" | "image-or-pdf" }[] = [
  { type: "PHOTO", accept: "image" }, { type: "ID_PROOF", accept: "image-or-pdf" }, { type: "ADDITIONAL_PHOTO_1", accept: "image" },
  { type: "ADDITIONAL_PHOTO_2", accept: "image" }, { type: "APPLICANT_SIGNATURE", accept: "image" }, { type: "INTRODUCER_SIGNATURE", accept: "image" },
];

export default function MemberDetailPage() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const { data: m, setData, loading, error, reload } = useApi<AdminMember>(`/admin/members/${id}`);
  const [editing, setEditing] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);
  const [linkOpen, setLinkOpen] = useState(false);
  const config = usePublicConfig();

  if (loading && !m) return <Loading label="Loading member" />;
  if (error || !m) return <ErrorState message={error ?? "Not found"} onRetry={reload} />;

  return (
    <>
      <Link to="/admin/members" className="mb-3 inline-block text-[15px] text-forest underline decoration-forest/30">Back to members</Link>
      {params.get("created") && !editing && <div className="mb-4"><Alert tone="success" title="Member added">Upload their photograph and documents below.</Alert></div>}
      <div className="mb-6 flex flex-wrap items-center gap-5 border border-line bg-white p-5">
        <Avatar src={m.photo_url} name={m.full_name ?? ""} size={88} />
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl sm:text-3xl">{m.full_name}</h1>
          <p className="text-ink-soft">S/o {m.father_name}</p>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-ink-muted">
            <StatusBadge status={m.status} /> {m.source === "MANUAL_ENTRY" ? "Entered by the office" : `Applied online (${m.application_number})`}, enrolled {formatDate(m.enrolled_at)}
          </p>
        </div>
        <div className="reg-stamp"><span className="text-[12px]">Regd. Mem. No.</span><span className="font-display text-2xl">{m.membership_number}</span></div>
      </div>

      {!editing && (
        <div className="mb-6 flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setEditing(true)}><Pencil className="h-4 w-4" /> Edit record</Button>
          <ButtonLink variant="secondary" to={`/admin/members/${m.member_id}/print`}><Printer className="h-4 w-4" /> Print record</ButtonLink>
          {!m.linked_user_id && <Button variant="secondary" onClick={() => setLinkOpen(true)}>Link to a login account</Button>}
          <Button variant={m.status === "ACTIVE" ? "quiet" : "primary"} className={m.status === "ACTIVE" ? "text-danger hover:text-danger" : ""} onClick={() => setStatusOpen(true)}>
            {m.status === "ACTIVE" ? "Deactivate membership" : "Reactivate membership"}
          </Button>
        </div>
      )}

      {editing ? (
        <EditMember m={m} bloodGroups={config.form.blood_groups} onCancel={() => setEditing(false)} onSaved={(x) => { setData(x); setEditing(false); }} />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[1fr_22rem]">
          <div className="space-y-6">
            <FormDataView data={m} aadhaar={m.aadhaar_number} />
            <Panel title="Photographs and documents">
              <div className="grid gap-3 md:grid-cols-2">
                {DOC_TYPES.map((d) => (
                  <FileUpload key={d.type} docType={d.type} uploadUrl={`/admin/members/${m.member_id}/documents`} accept={d.accept}
                    current={m.documents.find((x) => x.doc_type === d.type)} maxMb={d.type === "ID_PROOF" ? config.form.max_document_mb : config.form.max_photo_mb}
                    onUploaded={() => reload()} />
                ))}
              </div>
            </Panel>
          </div>
          <aside className="space-y-6">
            <Panel title="Office use">
              <div className="register">
                <RegisterRows rows={[
                  { label: "Verified by", value: m.verified_by }, { label: "Rec. No.", value: m.receipt_number },
                  { label: "Receipt date", value: m.receipt_date ? formatDate(m.receipt_date) : null },
                  { label: "Chairman", value: m.committee_chairman }, { label: "Secretary", value: m.committee_secretary },
                  { label: "President", value: m.committee_president }, { label: "Approved by", value: m.approved_by_name },
                  { label: "Notes", value: m.office_notes },
                ]} />
              </div>
            </Panel>
            <Panel title="Login account">
              {m.linked_user_email ? <p>Linked to <span className="font-medium">{m.linked_user_email}</span>.</p> : <p className="text-ink-soft">No login account. The member can't see the directory until an account is linked.</p>}
              {m.edit_permission_expires_at && <p className="mt-2 text-sm text-caution">Self-editing open until {formatDateTime(m.edit_permission_expires_at)}.</p>}
            </Panel>
            {m.status === "INACTIVE" && (
              <Alert tone="warning" title={`Deactivated ${formatDate(m.deactivated_at)}`}>{m.deactivation_reason}</Alert>
            )}
          </aside>
        </div>
      )}

      {!editing && (
        <Panel className="mt-6" title="Change history">
          {m.change_history.length === 0 ? <p className="text-ink-soft">No changes since the record was created.</p> : (
            <Table rows={m.change_history} rowKey={(r) => r.id} columns={[
              { key: "at", header: "When", render: (r) => <span className="text-sm">{formatDateTime(r.at)}</span> },
              { key: "f", header: "Field", render: (r) => fieldLabel(r.field) },
              { key: "o", header: "From", render: (r) => <span className="text-sm text-ink-muted">{r.old ?? "—"}</span> },
              { key: "n", header: "To", render: (r) => <span className="text-sm">{r.new ?? "—"}</span> },
              { key: "b", header: "By", render: (r) => <span className="text-sm">{r.changed_by ?? "—"} {r.source === "MEMBER_EDIT" ? "(member)" : ""}</span> },
            ]} />
          )}
        </Panel>
      )}

      <StatusModal open={statusOpen} m={m} onClose={() => setStatusOpen(false)} onDone={(x) => { setData(x); setStatusOpen(false); }} />
      <LinkModal open={linkOpen} m={m} onClose={() => setLinkOpen(false)} onDone={(x) => { setData(x); setLinkOpen(false); }} />
    </>
  );
}

function EditMember({ m, bloodGroups, onCancel, onSaved }: { m: AdminMember; bloodGroups: string[]; onCancel: () => void; onSaved: (m: AdminMember) => void }) {
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const office = Object.fromEntries(OFFICE_KEYS.map((k) => [k, (m[k] as string | null) ?? ""])) as unknown as OfficeValues;
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues & OfficeValues>({
    defaultValues: { ...toFormValues(m), declaration_date: m.declaration_date ?? "", ...office },
    resolver: formResolver(profileSchema()),
  });
  const onSubmit = handleSubmit(async (v) => {
    setError(null);
    try {
      const body = { ...toPayload(v, { includeDeclaration: false }), ...officePayload(v as unknown as Record<string, unknown>),
        declaration_place: v.declaration_place || null, declaration_date: v.declaration_date || null };
      const { data } = await api.put<AdminMember>(`/admin/members/${m.member_id}`, body);
      onSaved(data);
    } catch (e) {
      const info = parseApiError(e);
      setServerErrors(info.fieldErrors);
      setError(info.message);
    }
  });
  return (
    <form onSubmit={onSubmit} noValidate className="space-y-6">
      {error && <Alert tone="error">{error}</Alert>}
      <MembershipFormFields register={register as never} errors={errors} serverErrors={serverErrors} bloodGroups={bloodGroups}
        aadhaarMasked={m.aadhaar_masked} introducerRequired={false} />
      <FormSection title="Declaration">
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Place" {...register("declaration_place")} />
          <TextField label="Date" type="date" {...register("declaration_date")} />
        </div>
      </FormSection>
      <OfficeUseFields register={register} />
      <div className="sticky bottom-0 flex justify-end gap-2 border-t border-line bg-white/95 px-4 py-3">
        <Button variant="quiet" onClick={onCancel}>Cancel</Button>
        <Button type="submit" loading={isSubmitting}>Save changes</Button>
      </div>
    </form>
  );
}

function StatusModal({ open, m, onClose, onDone }: { open: boolean; m: AdminMember; onClose: () => void; onDone: (m: AdminMember) => void }) {
  const [reason, setReason] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const deactivate = m.status === "ACTIVE";
  async function submit() {
    if (deactivate && reason.trim().length < 5) return setErr("Give a reason (at least 5 characters).");
    setBusy(true);
    try {
      const { data } = await api.patch<AdminMember>(`/admin/members/${m.member_id}/status`, { status: deactivate ? "INACTIVE" : "ACTIVE", reason: reason || null });
      setReason("");
      onDone(data);
    } catch (e) { setErr(parseApiError(e).message); } finally { setBusy(false); }
  }
  return (
    <Modal open={open} onClose={onClose} title={deactivate ? "Deactivate this membership?" : "Reactivate this membership?"} footer={<>
      <Button variant="quiet" onClick={onClose}>Cancel</Button>
      <Button variant={deactivate ? "danger" : "primary"} loading={busy} onClick={submit}>{deactivate ? "Deactivate" : "Reactivate"}</Button>
    </>}>
      <p className="mb-3 text-[15px] text-ink-soft">{deactivate
        ? "The member disappears from both directories and loses member access. The record and number are kept and can be reactivated."
        : "The member will reappear in the directory and regain member access."}</p>
      <TextAreaField label={deactivate ? "Reason" : "Note (optional)"} rows={3} value={reason} onChange={(e) => setReason(e.target.value)} error={err ?? undefined} />
    </Modal>
  );
}

function LinkModal({ open, m, onClose, onDone }: { open: boolean; m: AdminMember; onClose: () => void; onDone: (m: AdminMember) => void }) {
  const [email, setEmail] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function submit() {
    setBusy(true);
    setErr(null);
    try {
      const { data } = await api.post<AdminMember>(`/admin/members/${m.member_id}/link-account`, { email });
      onDone(data);
    } catch (e) { const i = parseApiError(e); setErr(i.fieldErrors.email ?? i.message); } finally { setBusy(false); }
  }
  return (
    <Modal open={open} onClose={onClose} title="Link to a login account" footer={<>
      <Button variant="quiet" onClick={onClose}>Cancel</Button>
      <Button loading={busy} onClick={submit}>Link account</Button>
    </>}>
      <div className="space-y-3 text-[15px] text-ink-soft">
        <p>Ask {m.full_name} to create an account on this website and verify their email and mobile number. Then enter that account's email address here.</p>
        <p>Check their identity before linking: the account will see this membership and the member directory.</p>
        <TextField label="Account email address" type="email" value={email} onChange={(e) => setEmail(e.target.value)} error={err ?? undefined} />
      </div>
    </Modal>
  );
}
