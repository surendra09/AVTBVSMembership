import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useLocation } from "react-router-dom";
import { Printer } from "lucide-react";
import { Avatar, PageHeader, Panel, RegisterRows } from "@/components/ui/Data";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Alert, ErrorState, Loading, StatusBadge } from "@/components/ui/Feedback";
import { TextAreaField } from "@/components/ui/Form";
import { DocumentGallery, FormDataView } from "@/features/registration/ApplicationView";
import { useApi } from "@/hooks/useApi";
import { usePublicConfig } from "@/hooks/usePublicConfig";
import { api, parseApiError } from "@/services/api";
import type { EditRequest, MyMembership } from "@/types";
import { formatDate, formatDateTime, timeRemaining } from "@/utils/format";

export function MembershipStamp({ number, size = "lg" }: { number: string; size?: "lg" | "sm" }) {
  return (
    <div className="reg-stamp">
      <span className="text-[12px]">Regd. Mem. No.</span>
      <span className={`font-display leading-tight ${size === "lg" ? "text-3xl" : "text-xl"}`}>{number}</span>
    </div>
  );
}

const requestSchema = z.object({ reason: z.string().trim().min(10, "Explain what you need to change (at least 10 characters)").max(2000) });

export default function MyMembershipPage() {
  const { data: m, loading, error, reload } = useApi<MyMembership>("/members/me");
  const requests = useApi<EditRequest[]>(m?.status === "ACTIVE" ? "/members/edit-requests/me" : null);
  const { form } = usePublicConfig();
  const location = useLocation();
  const [sent, setSent] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<{ reason: string }>({ resolver: zodResolver(requestSchema) });

  useEffect(() => {
    if (location.hash === "#edit-request" && m) document.getElementById("edit-request")?.scrollIntoView({ behavior: "smooth" });
  }, [location.hash, m]);

  const onRequest = handleSubmit(async (values) => {
    setErr(null);
    try {
      await api.post("/members/edit-requests", values);
      setSent(true);
      reset();
      reload();
      requests.reload();
    } catch (e) {
      setErr(parseApiError(e).message);
    }
  });

  if (loading && !m) return <Loading label="Loading your membership" />;
  if (error || !m) return <ErrorState message={error ?? "Not found"} onRetry={reload} />;

  return (
    <>
      <PageHeader title="My membership" description="Your entry in the Sabha's membership register."
        actions={<ButtonLink variant="secondary" to="/dashboard/membership/print"><Printer className="h-4 w-4" /> Print record</ButtonLink>} />

      <div className="mb-6 flex flex-wrap items-center gap-6 border border-line bg-white p-5">
        <Avatar src={m.photo_url} name={m.full_name ?? ""} size={88} />
        <div className="min-w-0 flex-1">
          <p className="font-display text-2xl text-forest">{m.full_name}</p>
          <p className="text-ink-soft">S/o {m.father_name}</p>
          <p className="mt-1 flex items-center gap-2 text-sm text-ink-soft">Enrolled {formatDate(m.enrolled_at)} <StatusBadge status={m.status} /></p>
        </div>
        <MembershipStamp number={m.membership_number} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <div className="space-y-6">
          <FormDataView data={m} />
          <Panel title="Photographs and documents"><DocumentGallery documents={m.documents} /></Panel>
        </div>
        <div className="space-y-6">
          <section id="edit-request" className="scroll-mt-24">
            <Panel title="Change my details">
              {m.edit_permission_active ? (
                <div className="space-y-3">
                  <Alert tone="success" title="Editing is open">Ends {formatDateTime(m.edit_permission_expires_at)} ({timeRemaining(m.edit_permission_expires_at)}).</Alert>
                  <ButtonLink to="/dashboard/membership/edit" className="w-full">Edit my details</ButtonLink>
                </div>
              ) : m.pending_edit_request ? (
                <Alert tone="info" title="Request sent">An administrator will review your request. You'll be notified when it's decided.</Alert>
              ) : m.status !== "ACTIVE" ? (
                <p className="text-ink-soft">Changes are not possible while the membership is inactive.</p>
              ) : (
                <form onSubmit={onRequest} noValidate className="space-y-3">
                  <p className="text-[15px] text-ink-soft">
                    Approved details are locked. Ask an administrator for permission; once approved you'll have {form.edit_permission_hours} hours to make changes.
                  </p>
                  {sent && <Alert tone="success">Request sent.</Alert>}
                  {err && <Alert tone="error">{err}</Alert>}
                  <TextAreaField label="What needs to change, and why?" rows={4} error={errors.reason?.message} {...register("reason")} />
                  <Button type="submit" loading={isSubmitting} className="w-full">Request permission to edit</Button>
                </form>
              )}
            </Panel>
          </section>
          {requests.data && requests.data.length > 0 && (
            <Panel title="Previous requests">
              <ul className="space-y-3">
                {requests.data.map((r) => (
                  <li key={r.id} className="border-b border-line pb-3 last:border-0 last:pb-0">
                    <div className="flex items-center justify-between gap-2"><StatusBadge status={r.status} /><span className="text-[13px] text-ink-muted">{formatDate(r.created_at)}</span></div>
                    <p className="mt-1 text-[15px] text-ink-soft">{r.reason}</p>
                    {r.review_note && <p className="mt-1 text-sm text-ink-muted">Office note: {r.review_note}</p>}
                  </li>
                ))}
              </ul>
            </Panel>
          )}
          <Panel title="Declaration">
            <RegisterRows rows={[{ label: "Place", value: m.declaration_place }, { label: "Date", value: m.declaration_date ? formatDate(m.declaration_date) : null }]} />
          </Panel>
        </div>
      </div>
    </>
  );
}
