import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { PageHeader, Panel, RegisterRows } from "@/components/ui/Data";
import { Alert } from "@/components/ui/Feedback";
import { TextField } from "@/components/ui/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { api, parseApiError } from "@/services/api";
import type { Me } from "@/types";
import { formatDateTime } from "@/utils/format";
import { passwordSchema } from "@/utils/validation";

const pwSchema = z.object({ current_password: z.string().min(1, "Enter your current password"), new_password: passwordSchema, confirm: z.string() })
  .refine((v) => v.new_password === v.confirm, { path: ["confirm"], message: "Passwords do not match" });

export default function AccountPage() {
  const { me, setMe } = useAuth();
  const [nameMsg, setNameMsg] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [pwMsg, setPwMsg] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const nameForm = useForm<{ full_name: string }>({ defaultValues: { full_name: me?.user.full_name ?? "" },
    resolver: zodResolver(z.object({ full_name: z.string().trim().min(2, "Enter your name").max(150) })) });
  const pwForm = useForm<z.infer<typeof pwSchema>>({ resolver: zodResolver(pwSchema) });
  if (!me) return null;
  const roleLabel = { USER: "Member account", ADMIN: "Administrator", SUPER_ADMIN: "Super Admin" }[me.user.role];

  return (
    <>
      <PageHeader title="My account" description="Login details for AVTBVS Membership. Your membership record is kept separately." />
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Account">
          <div className="register mb-5">
            <RegisterRows rows={[
              { label: "Email address", value: <>{me.user.email} {me.user.email_verified ? <span className="text-sm text-ok">(verified)</span> : <span className="text-sm text-caution">(not verified)</span>}</> },
              { label: "Mobile number", value: <>{me.user.phone} {me.user.phone_verified ? <span className="text-sm text-ok">(verified)</span> : <span className="text-sm text-caution">(not verified)</span>}</> },
              { label: "Access level", value: roleLabel },
              { label: "Last login", value: formatDateTime(me.user.last_login_at) },
            ]} />
          </div>
          <form noValidate className="space-y-3" onSubmit={nameForm.handleSubmit(async (v) => {
            setNameMsg(null);
            try { const { data } = await api.put<Me>("/auth/me", v); setMe(data); setNameMsg({ tone: "success", text: "Name updated." }); }
            catch (e) { setNameMsg({ tone: "error", text: parseApiError(e).message }); }
          })}>
            {nameMsg && <Alert tone={nameMsg.tone}>{nameMsg.text}</Alert>}
            <TextField label="Display name" error={nameForm.formState.errors.full_name?.message} {...nameForm.register("full_name")} />
            <p className="text-sm text-ink-muted">To change your email address or mobile number, contact the Sabha office.</p>
            <Button type="submit" variant="secondary" loading={nameForm.formState.isSubmitting}>Save name</Button>
          </form>
        </Panel>
        <Panel title="Change password">
          <form noValidate className="space-y-4" onSubmit={pwForm.handleSubmit(async ({ confirm: _c, ...v }) => {
            setPwMsg(null);
            try { await api.post("/auth/change-password", v); pwForm.reset(); setPwMsg({ tone: "success", text: "Password changed. Other devices have been logged out." }); }
            catch (e) { const info = parseApiError(e); setPwMsg({ tone: "error", text: info.fieldErrors.current_password ?? info.message }); }
          })}>
            {pwMsg && <Alert tone={pwMsg.tone}>{pwMsg.text}</Alert>}
            <TextField label="Current password" type="password" autoComplete="current-password" error={pwForm.formState.errors.current_password?.message} {...pwForm.register("current_password")} />
            <TextField label="New password" type="password" autoComplete="new-password" hint="At least 10 characters, with a letter and a number" error={pwForm.formState.errors.new_password?.message} {...pwForm.register("new_password")} />
            <TextField label="Confirm new password" type="password" autoComplete="new-password" error={pwForm.formState.errors.confirm?.message} {...pwForm.register("confirm")} />
            <Button type="submit" loading={pwForm.formState.isSubmitting}>Change password</Button>
          </form>
        </Panel>
      </div>
    </>
  );
}
