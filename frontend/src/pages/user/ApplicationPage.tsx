import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { FileCheck2 } from "lucide-react";
import { FileUpload } from "@/components/FileUpload";
import { Button, ButtonLink } from "@/components/ui/Button";
import { PageHeader, Panel } from "@/components/ui/Data";
import { Alert, ErrorState, Loading, StatusBadge } from "@/components/ui/Feedback";
import { Checkbox, TextField } from "@/components/ui/Form";
import { ConfirmDialog } from "@/components/ui/Modal";
import { useAuth } from "@/features/auth/AuthContext";
import { DeclarationText, DocumentGallery, FormDataView, HistoryTimeline } from "@/features/registration/ApplicationView";
import { FormSection, MembershipFormFields } from "@/features/registration/MembershipFormFields";
import { draftSchema, submissionSchema, toFormValues, toPayload, type FormValues, formResolver } from "@/features/registration/formModel";
import { useApi } from "@/hooks/useApi";
import { usePublicConfig } from "@/hooks/usePublicConfig";
import { api, parseApiError } from "@/services/api";
import type { Application, DocumentItem, DocumentType } from "@/types";
import { DOC_LABEL, formatDateTime } from "@/utils/format";

const DOCS: { type: DocumentType; accept: "image" | "image-or-pdf"; required: boolean }[] = [
  { type: "PHOTO", accept: "image", required: true },
 /*  { type: "ADDITIONAL_PHOTO_1", accept: "image", required: true },
  { type: "ADDITIONAL_PHOTO_2", accept: "image", required: true }, */
  { type: "ID_PROOF", accept: "image-or-pdf", required: true },
  { type: "APPLICANT_SIGNATURE", accept: "image", required: true },
  { type: "INTRODUCER_SIGNATURE", accept: "image", required: true },
];

export default function ApplicationPage() {
  const { data: app, setData, loading, error, reload } = useApi<Application | null>("/applications/me");
  const { reload: reloadMe } = useAuth();
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  async function start() {
    setStarting(true);
    setStartError(null);
    try {
      const { data } = await api.post<Application>("/applications", {});
      setData(data);
      reloadMe();
    } catch (e) {
      setStartError(parseApiError(e).message);
    } finally {
      setStarting(false);
    }
  }

  if (loading && app === null) return <Loading label="Loading your application" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  if (!app || (app.status === "REJECTED" && starting)) {
    return (
      <>
        <PageHeader title="Life membership application" description="The online version of the Sabha's Life Membership Application Form." />
        <Panel>
          <div className="max-w-2xl space-y-4">
            <p>Before you start, keep these ready:</p>
            <ul className="list-disc space-y-1 pl-5 text-ink-soft">
              <li>A recent passport-size photograph and two more passport-size photographs</li>
              <li>Proof of identity (photo or PDF)</li>
              <li>A photo of your signature</li>
              <li>Your introducer's name, phone number and membership registration number</li>
            </ul>
            <p className="text-ink-soft">Your progress is saved as a draft, so you can finish the form later.</p>
            {startError && <Alert tone="error">{startError}</Alert>}
            <Button onClick={start} loading={starting}>Start the application</Button>
          </div>
        </Panel>
      </>
    );
  }

  if (app.can_edit) return <EditableApplication app={app} onChange={(a) => { setData(a); reloadMe(); }} />;
  return <ApplicationStatusView app={app} onStartNew={start} starting={starting} startError={startError} />;
}

function ApplicationStatusView({ app, onStartNew, starting, startError }: { app: Application; onStartNew: () => void; starting: boolean; startError: string | null }) {
  const { organisation } = usePublicConfig();
  return (
    <>
      <PageHeader title="Your application" description={<>Application no. <span className="font-medium text-ink">{app.application_number}</span></>}
        actions={<StatusBadge status={app.status} />} />
      <div className="mb-6 space-y-3">
        {(app.status === "PENDING" || app.status === "RESUBMITTED") && (
          <Alert tone="info" title="Waiting for verification">
            Submitted on {formatDateTime(app.last_submitted_at)}. The Membership Enrollment Committee will review it. You'll be notified by SMS, email and here. The application can't be changed while it is being reviewed.
          </Alert>
        )}
        {app.status === "APPROVED" && (
          <Alert tone="success" title="Your membership is approved" action={<ButtonLink size="sm" to="/dashboard/membership">View membership</ButtonLink>}>
            Your membership number is {app.membership_number}.
          </Alert>
        )}
        {app.status === "REJECTED" && (
          <Alert tone="error" title="Your application was not approved"
            action={<Button size="sm" variant="secondary" onClick={onStartNew} loading={starting}>Start a new application</Button>}>
            {app.rejection_reason}
          </Alert>
        )}
        {startError && <Alert tone="error">{startError}</Alert>}
      </div>
      <div className="grid gap-6 lg:grid-cols-[1fr_18rem]">
        <div className="space-y-6">
          <FormDataView data={app} />
          <Panel title="Declaration">
            <DeclarationText name={app.full_name} father={app.father_name} community={organisation.community_name} />
            <p className="mt-3 text-[15px] text-ink-soft">Place: {app.declaration_place} &nbsp; Date: {app.declaration_date}</p>
          </Panel>
          <Panel title="Photographs and documents"><DocumentGallery documents={app.documents} /></Panel>
        </div>
        <Panel title="History"><HistoryTimeline history={app.history} /></Panel>
      </div>
    </>
  );
}

function EditableApplication({ app, onChange }: { app: Application; onChange: (a: Application) => void }) {
  const config = usePublicConfig();
  const { me } = useAuth();
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [docs, setDocs] = useState<DocumentItem[]>(app.documents);
  const isCorrection = app.status === "CORRECTION_REQUIRED";

  const fullSchema = useMemo(() => submissionSchema(config.form.minimum_age_years), [config.form.minimum_age_years]);
  // The resolver checks formats only, so drafts can be saved half-complete.
  const { register, handleSubmit, watch, getValues, setError, clearErrors, formState: { errors } } = useForm<FormValues>({
    defaultValues: toFormValues(app),
    resolver: formResolver(draftSchema),
  });
  useEffect(() => setDocs(app.documents), [app.documents]);
  const [name, father] = watch(["full_name", "father_name"]);

  const docByType = (t: DocumentType) => docs.find((d) => d.doc_type === t);
  const requiredDocs = DOCS.filter((d) => d.required || (d.type === "INTRODUCER_SIGNATURE" && config.form.require_introducer_signature));
  const missingDocs = requiredDocs.filter((d) => !docByType(d.type));

  async function save(values: FormValues): Promise<Application | null> {
    setServerErrors({});
    try {
      const { data } = await api.put<Application>(`/applications/${app.id}`, toPayload(values));
      onChange(data);
      return data;
    } catch (e) {
      const info = parseApiError(e, "Could not save.");
      setServerErrors(info.fieldErrors);
      setMessage({ tone: "error", text: info.message });
      return null;
    }
  }

  const onSaveDraft = handleSubmit(async (values) => {
    setSaving(true);
    setMessage(null);
    const saved = await save(values);
    if (saved) setMessage({ tone: "success", text: `Draft saved at ${new Date().toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" })}.` });
    setSaving(false);
  }, () => setMessage({ tone: "error", text: "Some entries are not in the right format. Please check the highlighted fields." }));

  const onReview = () => {
    clearErrors();
    const result = fullSchema.safeParse(getValues());
    if (!result.success) {
      for (const issue of result.error.issues) {
        const key = issue.path[0] as keyof FormValues;
        if (key && !errors[key]) setError(key, { type: "manual", message: issue.message });
      }
      setMessage({ tone: "error", text: "Please complete the highlighted fields before submitting." });
      setTimeout(() => document.querySelector("[aria-invalid='true']")?.scrollIntoView({ behavior: "smooth", block: "center" }), 0);
      return;
    }
    if (missingDocs.length) {
      setMessage({ tone: "error", text: `Please upload: ${missingDocs.map((d) => DOC_LABEL[d.type].toLowerCase()).join("; ")}.` });
      return;
    }
    if (!me?.user.phone_verified) {
      setMessage({ tone: "error", text: "Verify your mobile number from the dashboard before submitting." });
      return;
    }
    setMessage(null);
    setConfirmOpen(true);
  };

  async function doSubmit() {
    setSubmitting(true);
    const saved = await save(getValues());
    if (!saved) { setSubmitting(false); setConfirmOpen(false); return; }
    try {
      const { data } = await api.post<Application>(`/applications/${app.id}/${isCorrection ? "resubmit" : "submit"}`);
      setConfirmOpen(false);
      onChange(data);
      window.scrollTo({ top: 0 });
    } catch (e) {
      const info = parseApiError(e, "Could not submit.");
      setServerErrors(info.fieldErrors);
      setMessage({ tone: "error", text: info.message });
      setConfirmOpen(false);
    } finally {
      setSubmitting(false);
    }
  }

  async function removeDoc(doc: DocumentItem) {
    await api.delete(`/applications/${app.id}/documents/${doc.id}`);
    setDocs((d) => d.filter((x) => x.id !== doc.id));
  }

  const declErr = errors.declaration_accepted?.message ?? serverErrors.declaration_accepted;
  return (
    <>
      <PageHeader title={isCorrection ? "Correct your application" : "Life membership application"}
        description={<>Application no. <span className="font-medium text-ink">{app.application_number}</span>. Fields marked <span className="text-register">*</span> are required.</>}
        actions={<StatusBadge status={app.status} />} />

      {isCorrection && (
        <div className="mb-6">
          <Alert tone="warning" title="The office has asked for these corrections">{app.correction_notes}</Alert>
        </div>
      )}
      {!me?.user.phone_verified && (
        <div className="mb-6">
          <Alert tone="warning" title="Verify your mobile number" action={<Link to="/dashboard" className="text-sm font-medium underline">Verify now</Link>}>
            You can fill in the form now, but you need to verify your mobile number before submitting.
          </Alert>
        </div>
      )}

      <form onSubmit={(e) => { e.preventDefault(); onReview(); }} noValidate className="space-y-6">
        <MembershipFormFields register={register} errors={errors} serverErrors={serverErrors} bloodGroups={config.form.blood_groups}
          aadhaarMasked={app.aadhaar_masked} />

        <FormSection title="Photographs and documents" description="The paper form asks you to enclose proof of ID and two passport-size photos, in addition to the photo affixed to the form.">
          <div className="grid gap-3 md:grid-cols-2">
            {DOCS.map((d) => (
              <FileUpload key={d.type} docType={d.type} uploadUrl={`/applications/${app.id}/documents`} current={docByType(d.type)}
                required={d.required || (d.type === "INTRODUCER_SIGNATURE" && config.form.require_introducer_signature)}
                accept={d.accept} maxMb={d.type === "ID_PROOF" ? config.form.max_document_mb : config.form.max_photo_mb}
                hint={d.type === "INTRODUCER_SIGNATURE" && !config.form.require_introducer_signature ? "Optional. JPG or PNG" : undefined}
                error={serverErrors[`document_${d.type}`]}
                onUploaded={(doc) => setDocs((list) => [...list.filter((x) => x.doc_type !== doc.doc_type), doc])}
                onRemove={removeDoc} />
            ))}
          </div>
        </FormSection>

        <FormSection title="Declaration">
          <DeclarationText name={name} father={father} community={config.organisation.community_name} />
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField label="Place" required error={errors.declaration_place?.message ?? serverErrors.declaration_place} {...register("declaration_place")} />
            <TextField label="Date" type="date" required error={errors.declaration_date?.message ?? serverErrors.declaration_date} {...register("declaration_date")} />
          </div>
          <Checkbox label="I confirm the declaration above and that the information in this form is true." error={declErr} {...register("declaration_accepted")} />
        </FormSection>

        <div className="sticky bottom-0 z-10 -mx-4 border-t border-line bg-white/95 px-4 py-3 backdrop-blur sm:mx-0 sm:border sm:px-5">
          {message && <div className="mb-3"><Alert tone={message.tone}>{message.text}</Alert></div>}
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Button variant="secondary" onClick={() => onSaveDraft()} loading={saving}>Save draft</Button>
            <Button type="submit"><FileCheck2 className="h-4 w-4" />{isCorrection ? "Resubmit application" : "Submit application"}</Button>
          </div>
        </div>
      </form>

      <ConfirmDialog open={confirmOpen} title={isCorrection ? "Resubmit your application?" : "Submit your application?"}
        confirmLabel={isCorrection ? "Resubmit" : "Submit"} onConfirm={doSubmit} onCancel={() => setConfirmOpen(false)} loading={submitting}>
        <p>After you submit, you can't change the application unless the office asks for corrections.</p>
        <p>You'll be notified by SMS, email and on this website when it has been reviewed.</p>
      </ConfirmDialog>
    </>
  );
}
