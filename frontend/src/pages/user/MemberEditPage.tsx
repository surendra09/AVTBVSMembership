import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { FileUpload } from "@/components/FileUpload";
import { Button, ButtonLink } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/Data";
import { Alert, ErrorState, Loading } from "@/components/ui/Feedback";
import { ConfirmDialog } from "@/components/ui/Modal";
import { useAuth } from "@/features/auth/AuthContext";
import { FormSection, MembershipFormFields } from "@/features/registration/MembershipFormFields";
import { profileSchema, toFormValues, toPayload, type FormValues, formResolver } from "@/features/registration/formModel";
import { useApi } from "@/hooks/useApi";
import { usePublicConfig } from "@/hooks/usePublicConfig";
import { api, parseApiError } from "@/services/api";
import type { DocumentType, MyMembership } from "@/types";
import { formatDateTime, timeRemaining } from "@/utils/format";

const REPLACEABLE: { type: DocumentType; accept: "image" | "image-or-pdf" }[] = [
  { type: "PHOTO", accept: "image" }, { type: "ID_PROOF", accept: "image-or-pdf" }, { type: "APPLICANT_SIGNATURE", accept: "image" },
];

export default function MemberEditPage() {
  const { data: m, setData, loading, error, reload } = useApi<MyMembership>("/members/me");
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 30_000); return () => clearInterval(t); }, []);

  if (loading && !m) return <Loading />;
  if (error || !m) return <ErrorState message={error ?? "Not found"} onRetry={reload} />;
  const expired = !m.edit_permission_active || !m.edit_permission_expires_at || new Date(m.edit_permission_expires_at).getTime() <= now;
  if (expired) {
    return (
      <>
        <PageHeader title="Edit my details" />
        <Alert tone="warning" title="Editing is not open" action={<ButtonLink size="sm" to="/dashboard/membership#edit-request">Request permission</ButtonLink>}>
          Your approved details are locked. Send a request to the administrators to get a 24-hour editing window.
        </Alert>
      </>
    );
  }
  return <EditForm m={m} onSaved={setData} now={now} />;
}

function EditForm({ m, onSaved, now }: { m: MyMembership; onSaved: (m: MyMembership) => void; now: number }) {
  const config = usePublicConfig();
  const { reload: reloadMe } = useAuth();
  const navigate = useNavigate();
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [confirm, setConfirm] = useState<FormValues | null>(null);
  const [saving, setSaving] = useState(false);
  const { register, handleSubmit, formState: { errors, isDirty }, reset } = useForm<FormValues>({
    defaultValues: toFormValues(m), resolver: formResolver(profileSchema(config.form.minimum_age_years)),
  });

  async function save(values: FormValues) {
    setSaving(true);
    setServerErrors({});
    try {
      const payload = toPayload(values, { includeIntroducer: false, includeDeclaration: false });
      const { data } = await api.put<MyMembership>("/members/profile", payload);
      onSaved(data);
      reset(toFormValues(data));
      setMessage({ tone: "success", text: "Your changes are saved and the office has been notified." });
      setConfirm(null);
      reloadMe();
    } catch (e) {
      const info = parseApiError(e, "Could not save.");
      setServerErrors(info.fieldErrors);
      setMessage({ tone: "error", text: info.message });
      setConfirm(null);
      if (info.status === 403) setTimeout(() => navigate("/dashboard/membership"), 2500);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader title="Edit my details" description={<>Membership no. {m.membership_number}</>} />
      <div className="mb-6">
        <Alert tone="info" title={`Editing closes ${formatDateTime(m.edit_permission_expires_at)}`}>
          {timeRemaining(m.edit_permission_expires_at, now)}. Every change is recorded and the office is notified. Introducer details can't be changed.
        </Alert>
      </div>
      <form onSubmit={handleSubmit((v) => setConfirm(v))} noValidate className="space-y-6">
        <MembershipFormFields register={register} errors={errors} serverErrors={serverErrors} bloodGroups={config.form.blood_groups}
          aadhaarMasked={m.aadhaar_masked} lockIntroducer introducerRequired={false} />
        <FormSection title="Replace photograph or documents">
          <div className="grid gap-3 md:grid-cols-2">
            {REPLACEABLE.map((d) => (
              <FileUpload key={d.type} docType={d.type} uploadUrl="/members/profile/documents" accept={d.accept}
                current={m.documents.find((x) => x.doc_type === d.type)}
                maxMb={d.type === "ID_PROOF" ? config.form.max_document_mb : config.form.max_photo_mb}
                onUploaded={(doc) => onSaved({ ...m, documents: [...m.documents.filter((x) => x.doc_type !== doc.doc_type), doc],
                  photo_url: doc.doc_type === "PHOTO" ? doc.url : m.photo_url })} />
            ))}
          </div>
        </FormSection>
        <div className="sticky bottom-0 z-10 -mx-4 border-t border-line bg-white/95 px-4 py-3 backdrop-blur sm:mx-0 sm:border sm:px-5">
          {message && <div className="mb-3"><Alert tone={message.tone}>{message.text}</Alert></div>}
          <div className="flex justify-end gap-2">
            <ButtonLink variant="quiet" to="/dashboard/membership">Back</ButtonLink>
            <Button type="submit" disabled={!isDirty}>Save changes</Button>
          </div>
        </div>
      </form>
      <ConfirmDialog open={!!confirm} title="Save these changes?" confirmLabel="Save changes" loading={saving}
        onConfirm={() => confirm && save(confirm)} onCancel={() => setConfirm(null)}>
        <p>Your membership record will be updated and the change recorded in its history.</p>
      </ConfirmDialog>
    </>
  );
}
