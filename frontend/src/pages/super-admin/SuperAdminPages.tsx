import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ShieldCheck, UserCog, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { PageHeader, Pagination, Panel, RegisterRows, SearchInput, Table } from "@/components/ui/Data";
import { Alert, ErrorState, Loading, StatusBadge } from "@/components/ui/Feedback";
import { SelectField, TextField } from "@/components/ui/Form";
import { ConfirmDialog, Modal } from "@/components/ui/Modal";
import { useAuth } from "@/features/auth/AuthContext";
import { useApi, useDebounced } from "@/hooks/useApi";
import { api, parseApiError } from "@/services/api";
import { StatStrip } from "@/pages/admin/AdminDashboard";
import type { AdminAccount, Role } from "@/types";
import { formatDateTime } from "@/utils/format";
import { passwordSchema, phoneSchema } from "@/utils/validation";

const ROLE_NAME: Record<Role, string> = { USER: "Member account", ADMIN: "Admin", SUPER_ADMIN: "Super Admin" };
const ACTION_LABEL: Record<string, string> = {
  "application.approve": "Approved an application", "application.reject": "Rejected an application",
  "application.request_corrections": "Requested corrections", "application.view": "Opened an application",
  "member.manual_add": "Added an existing member", "member.admin_edit": "Edited a member record", "member.status": "Changed membership status",
  "member.view": "Opened a member record", "member.upload": "Uploaded a member document", "member.link_account": "Linked a login account",
  "edit_request.approve": "Approved a profile edit request", "edit_request.reject": "Declined a profile edit request",
  "edit_permission.revoke": "Ended editing access", "admin.create": "Created an admin", "admin.promote": "Gave admin access",
  "admin.update": "Edited an admin", "admin.activate": "Activated an admin", "admin.deactivate": "Deactivated an admin",
  "settings.membership_sequence": "Changed the membership number sequence", "report.export_members": "Exported the member list",
  "delivery.retry": "Retried a message", "auth.login": "Logged in", "auth.login_failed": "Failed login attempt",
};
const actionLabel = (a: string) => ACTION_LABEL[a] ?? a.replace(/[._]/g, " ");

interface SuperStats {
  total_members: number; active_members: number; total_admins: number; active_admins: number; pending_applications: number; total_applications: number;
  recent_admin_activity: { id: number; actor: string; role: string; action: string; entity_type: string | null; entity_id: string | null; at: string }[];
}

export function SuperAdminDashboard() {
  const { data, loading, error, reload } = useApi<SuperStats>("/super-admin/dashboard");
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? ""} onRetry={reload} />;
  return (
    <>
      <PageHeader title="Super Admin" description="Oversight of administrators and all membership activity." />
      <StatStrip items={[
        { label: "Total members", value: data.total_members, to: "/admin/members" },
        { label: "Active members", value: data.active_members, to: "/admin/members?status=ACTIVE" },
        { label: "Total admins", value: data.total_admins, to: "/super-admin/admins" },
        { label: "Active admins", value: data.active_admins, to: "/super-admin/admins" },
        { label: "Pending applications", value: data.pending_applications, to: "/admin/applications/pending", emphasis: true },
        { label: "Total applications", value: data.total_applications, to: "/admin/applications" },
      ]} />
      <Panel className="mt-6" title="Recent admin activity">
        {data.recent_admin_activity.length === 0 ? <p className="text-ink-soft">No administrative actions yet.</p> : (
          <ul className="divide-y divide-line">
            {data.recent_admin_activity.map((a) => (
              <li key={a.id} className="flex flex-wrap justify-between gap-2 py-2.5">
                <span><span className="font-medium">{a.actor}</span> <span className="text-ink-soft">{actionLabel(a.action).toLowerCase()}</span>
                  {a.entity_id && <span className="text-ink-muted"> ({a.entity_type} {a.entity_id})</span>}</span>
                <span className="text-sm text-ink-muted">{formatDateTime(a.at)}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </>
  );
}

const createSchema = z.object({
  full_name: z.string().trim().min(2, "Enter the full name"), email: z.string().trim().email("Enter a valid email address"),
  phone: phoneSchema, role: z.enum(["ADMIN", "SUPER_ADMIN"]),
  temporary_password: z.union([z.literal(""), passwordSchema]),
});

export function AdminManagementPage({ startCreate = false }: { startCreate?: boolean }) {
  const { me } = useAuth();
  const { data, setData, loading, error, reload } = useApi<AdminAccount[]>("/super-admin/admins");
  const [createOpen, setCreateOpen] = useState(startCreate);
  const [promoteOpen, setPromoteOpen] = useState(false);
  const [edit, setEdit] = useState<AdminAccount | null>(null);
  const [toggle, setToggle] = useState<AdminAccount | null>(null);
  const [toggleErr, setToggleErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const upsert = (a: AdminAccount) => setData((list) => list ? (list.some((x) => x.id === a.id) ? list.map((x) => (x.id === a.id ? a : x)) : [...list, a]) : [a]);

  async function doToggle() {
    if (!toggle) return;
    setBusy(true);
    setToggleErr(null);
    try {
      const { data } = await api.patch<AdminAccount>(`/super-admin/admins/${toggle.id}/status`, { is_active: !toggle.is_active });
      upsert(data);
      setToggle(null);
    } catch (e) { setToggleErr(parseApiError(e).message); } finally { setBusy(false); }
  }

  return (
    <>
      <PageHeader title="Admin management" description="Only Super Admins can create administrators or change their access."
        actions={<>
          <Button variant="secondary" onClick={() => setPromoteOpen(true)}><UserCog className="h-4 w-4" /> Convert existing user</Button>
          <Button onClick={() => setCreateOpen(true)}><UserPlus className="h-4 w-4" /> Create admin</Button>
        </>} />
      {notice && <div className="mb-4"><Alert tone="success">{notice}</Alert></div>}
      {loading && !data ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data && (
        <Table caption="Administrators" rows={data} rowKey={(r) => r.id} columns={[
          { key: "n", header: "Name", render: (r) => <span><span className="block font-medium">{r.full_name}{r.id === me?.user.id && <span className="ml-1 text-sm text-ink-muted">(you)</span>}</span><span className="block text-sm text-ink-muted">{r.email}</span></span> },
          { key: "p", header: "Mobile", render: (r) => r.phone },
          { key: "r", header: "Role", render: (r) => <span className="inline-flex items-center gap-1">{r.role === "SUPER_ADMIN" && <ShieldCheck className="h-4 w-4 text-register" />}{ROLE_NAME[r.role]}</span> },
          { key: "m", header: "Member no.", render: (r) => r.membership_number ?? "—" },
          { key: "l", header: "Last login", render: (r) => <span className="text-sm">{formatDateTime(r.last_login_at)}</span> },
          { key: "s", header: "Status", render: (r) => <StatusBadge status={r.is_active ? "ACTIVE" : "INACTIVE"} /> },
          { key: "a", header: "", render: (r) => (
            <span className="flex gap-1">
              <Button size="sm" variant="ghost" onClick={() => setEdit(r)}>Edit</Button>
              {r.id !== me?.user.id && <Button size="sm" variant="ghost" onClick={() => setToggle(r)}>{r.is_active ? "Deactivate" : "Activate"}</Button>}
            </span>) },
        ]} />
      )}
      <CreateAdminModal open={createOpen} onClose={() => setCreateOpen(false)} onCreated={(a, invited) => {
        upsert(a); setCreateOpen(false);
        setNotice(invited ? `${a.full_name} has been emailed a link to set their password.` : `${a.full_name} can now log in with the temporary password. Ask them to change it.`);
      }} />
      <PromoteModal open={promoteOpen} onClose={() => setPromoteOpen(false)} onDone={(a) => { upsert(a); setPromoteOpen(false); setNotice(`${a.full_name} is now an ${ROLE_NAME[a.role]}.`); }} />
      <EditAdminModal admin={edit} onClose={() => setEdit(null)} onDone={(a) => { if (a.role === "USER") { setData((l) => l?.filter((x) => x.id !== a.id) ?? null); } else upsert(a); setEdit(null); }} />
      <ConfirmDialog open={!!toggle} title={toggle?.is_active ? `Deactivate ${toggle?.full_name}?` : `Activate ${toggle?.full_name}?`}
        confirmLabel={toggle?.is_active ? "Deactivate" : "Activate"} danger={toggle?.is_active} loading={busy} onConfirm={doToggle} onCancel={() => { setToggle(null); setToggleErr(null); }}>
        <p>{toggle?.is_active ? "They will be logged out and won't be able to log in until reactivated." : "They will be able to log in again with their existing password."}</p>
        {toggleErr && <Alert tone="error">{toggleErr}</Alert>}
      </ConfirmDialog>
    </>
  );
}

function CreateAdminModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (a: AdminAccount, invited: boolean) => void }) {
  const [err, setErr] = useState<string | null>(null);
  const { register, handleSubmit, reset, setError, formState: { errors, isSubmitting } } = useForm<z.infer<typeof createSchema>>({
    resolver: zodResolver(createSchema), defaultValues: { role: "ADMIN", temporary_password: "" },
  });
  const submit = handleSubmit(async (v) => {
    setErr(null);
    try {
      const { data } = await api.post<AdminAccount>("/super-admin/admins", { ...v, temporary_password: v.temporary_password || null });
      reset();
      onCreated(data, !v.temporary_password);
    } catch (e) {
      const info = parseApiError(e);
      Object.entries(info.fieldErrors).forEach(([k, m]) => setError(k as "email", { message: m }));
      setErr(info.message);
    }
  });
  return (
    <Modal open={open} onClose={onClose} title="Create an admin account" footer={<>
      <Button variant="quiet" onClick={onClose}>Cancel</Button><Button onClick={submit} loading={isSubmitting}>Create account</Button></>}>
      <form onSubmit={submit} noValidate className="space-y-4">
        {err && <Alert tone="error">{err}</Alert>}
        <TextField label="Full name" required error={errors.full_name?.message} {...register("full_name")} />
        <TextField label="Email address" type="email" required error={errors.email?.message} {...register("email")} />
        <TextField label="Mobile number" type="tel" required error={errors.phone?.message} {...register("phone")} />
        <SelectField label="Role" options={[{ value: "ADMIN", label: "Admin (membership management)" }, { value: "SUPER_ADMIN", label: "Super Admin (also manages admins)" }]} {...register("role")} />
        <TextField label="Temporary password" type="password" autoComplete="new-password"
          hint="Leave blank to email them a link to set their own password (recommended)." error={errors.temporary_password?.message} {...register("temporary_password")} />
      </form>
    </Modal>
  );
}

function PromoteModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: (a: AdminAccount) => void }) {
  const [q, setQ] = useState("");
  const [role, setRole] = useState<"ADMIN" | "SUPER_ADMIN">("ADMIN");
  const [picked, setPicked] = useState<AdminAccount | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const dq = useDebounced(q);
  const results = useApi<AdminAccount[]>(dq.length >= 2 ? "/super-admin/users/search" : null, { q: dq });
  async function submit() {
    if (!picked) return setErr("Choose a person from the search results.");
    setBusy(true);
    try {
      const { data } = await api.post<AdminAccount>("/super-admin/admins/promote", { email: picked.email, role });
      setPicked(null); setQ(""); onDone(data);
    } catch (e) { setErr(parseApiError(e).message); } finally { setBusy(false); }
  }
  return (
    <Modal open={open} onClose={onClose} title="Convert an existing user into an admin" footer={<>
      <Button variant="quiet" onClick={onClose}>Cancel</Button><Button onClick={submit} loading={busy} disabled={!picked}>Give admin access</Button></>}>
      <div className="space-y-4">
        <SearchInput value={q} onChange={(v) => { setQ(v); setPicked(null); }} placeholder="Search by name, email or mobile" />
        {results.data && (
          <ul className="max-h-56 overflow-auto border border-line">
            {results.data.length === 0 && <li className="px-3 py-3 text-sm text-ink-muted">No matching accounts.</li>}
            {results.data.map((u) => (
              <li key={u.id}>
                <button onClick={() => setPicked(u)} className={`block w-full px-3 py-2 text-left hover:bg-ivory ${picked?.id === u.id ? "bg-forest-50" : ""}`}>
                  <span className="block font-medium">{u.full_name}</span>
                  <span className="block text-sm text-ink-muted">{u.email}{u.membership_number ? `, member no. ${u.membership_number}` : ""}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <SelectField label="Role" value={role} onChange={(e) => setRole(e.target.value as "ADMIN")} options={[{ value: "ADMIN", label: "Admin" }, { value: "SUPER_ADMIN", label: "Super Admin" }]} />
        {err && <Alert tone="error">{err}</Alert>}
      </div>
    </Modal>
  );
}

function EditAdminModal({ admin, onClose, onDone }: { admin: AdminAccount | null; onClose: () => void; onDone: (a: AdminAccount) => void }) {
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [role, setRole] = useState<Role>("ADMIN");
  const [lastId, setLastId] = useState<number | null>(null);
  if (admin && admin.id !== lastId) { setLastId(admin.id); setName(admin.full_name); setPhone(admin.phone); setRole(admin.role); setErr(null); }
  async function submit() {
    if (!admin) return;
    setBusy(true);
    setErr(null);
    try {
      const body: Record<string, unknown> = {};
      if (name !== admin.full_name) body.full_name = name;
      if (phone !== admin.phone) body.phone = phone;
      if (role !== admin.role) body.role = role;
      const { data } = await api.put<AdminAccount>(`/super-admin/admins/${admin.id}`, body);
      onDone(data);
    } catch (e) { const i = parseApiError(e); setErr(Object.values(i.fieldErrors)[0] ?? i.message); } finally { setBusy(false); }
  }
  return (
    <Modal open={!!admin} onClose={onClose} title={`Edit ${admin?.full_name ?? ""}`} footer={<>
      <Button variant="quiet" onClick={onClose}>Cancel</Button><Button onClick={submit} loading={busy}>Save</Button></>}>
      <div className="space-y-4">
        {err && <Alert tone="error">{err}</Alert>}
        <TextField label="Full name" value={name} onChange={(e) => setName(e.target.value)} />
        <TextField label="Mobile number" value={phone} onChange={(e) => setPhone(e.target.value)} hint="Changing it requires the admin to verify the new number." />
        <SelectField label="Access level" value={role} onChange={(e) => setRole(e.target.value as Role)} options={[
          { value: "ADMIN", label: "Admin" }, { value: "SUPER_ADMIN", label: "Super Admin" }, { value: "USER", label: "Remove admin access" }]} />
        {role === "USER" && <Alert tone="warning">They will lose access to all administrative pages and be logged out.</Alert>}
      </div>
    </Modal>
  );
}

interface AuditRow { id: number; actor: string | null; actor_role: string | null; action: string; entity_type: string | null; entity_id: string | null; details: Record<string, unknown> | null; ip_address: string | null; created_at: string }

export function AuditLogPage() {
  const [action, setAction] = useState("");
  const [adminOnly, setAdminOnly] = useState(true);
  const [page, setPage] = useState(1);
  const da = useDebounced(action);
  const { data, loading, error, reload } = useApi<{ items: AuditRow[]; total: number; page: number; pages: number }>("/super-admin/audit-logs", { action: da || undefined, admin_only: adminOnly, page });
  return (
    <>
      <PageHeader title="Admin activity" description="Every administrative action, including who opened records containing Aadhaar numbers." />
      <div className="mb-4 flex flex-wrap items-center gap-4">
        <SearchInput className="w-full sm:w-80" value={action} onChange={(v) => { setAction(v); setPage(1); }} placeholder="Filter by action, e.g. approve" />
        <label className="flex items-center gap-2 text-[15px]"><input type="checkbox" className="accent-forest" checked={adminOnly} onChange={(e) => { setAdminOnly(e.target.checked); setPage(1); }} /> Administrators only</label>
      </div>
      {loading && !data ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data && (
        <>
          <Table caption="Audit log" rows={data.items} rowKey={(r) => r.id} columns={[
            { key: "t", header: "When", render: (r) => <span className="text-sm">{formatDateTime(r.created_at)}</span> },
            { key: "a", header: "Who", render: (r) => <span>{r.actor ?? "System"}<span className="block text-[12px] text-ink-muted">{r.actor_role ? ROLE_NAME[r.actor_role as Role] : ""}</span></span> },
            { key: "w", header: "Action", render: (r) => actionLabel(r.action) },
            { key: "e", header: "Record", render: (r) => <span className="text-sm text-ink-soft">{r.entity_type ? `${r.entity_type.replace(/_/g, " ")} ${r.entity_id ?? ""}` : "—"}</span> },
            { key: "d", header: "Details", render: (r) => <span className="line-clamp-2 max-w-xs text-[13px] text-ink-muted">{r.details ? Object.entries(r.details).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : String(v)}`).join("; ") : ""}</span> },
            { key: "ip", header: "IP", render: (r) => <span className="text-[13px] text-ink-muted">{r.ip_address ?? ""}</span> },
          ]} />
          <Pagination page={data.page} pages={data.pages} total={data.total} onPage={setPage} noun="entries" />
        </>
      )}
    </>
  );
}

interface SettingsView {
  organisation: Record<string, string>;
  membership_numbering: { sequence: string; next_value: number; template: string; prefix: string; per_year: boolean; examples: string[] };
  rules: Record<string, number | boolean>;
  providers: { email: string; sms: string };
  environment: string;
  configuration_warnings: string[];
}

export function SystemSettingsPage() {
  const { data, setData, loading, error, reload } = useApi<SettingsView>("/super-admin/settings");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [msg, setMsg] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? ""} onRetry={reload} />;
  const n = data.membership_numbering;
  async function save() {
    setBusy(true);
    try {
      const { data: preview } = await api.put<SettingsView["membership_numbering"]>("/super-admin/settings/membership-sequence", { next_value: Number(next) });
      setData((d) => d && { ...d, membership_numbering: preview });
      setMsg({ tone: "success", text: `The next approved member will receive ${preview.examples[0]}.` });
      setNext("");
    } catch (e) { setMsg({ tone: "error", text: parseApiError(e).message }); } finally { setBusy(false); setConfirm(false); }
  }
  const yes = (v: unknown) => (v ? "Yes" : "No");
  return (
    <>
      <PageHeader title="System settings" description="Organisation details and business rules come from the server configuration (.env). The membership number sequence can be adjusted here." />
      {data.configuration_warnings.map((w) => <div key={w} className="mb-4"><Alert tone="warning">{w}</Alert></div>)}
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Membership numbers">
          <div className="register mb-4">
            <RegisterRows rows={[
              { label: "Format template", value: <code className="text-sm">{n.template}</code> },
              { label: "Prefix", value: n.prefix || "(none)" },
              { label: "Restarts each year", value: yes(n.per_year) },
              { label: "Next sequence value", value: n.next_value },
              { label: "Next numbers", value: n.examples.join(", ") },
            ]} />
          </div>
          <p className="mb-3 text-[15px] text-ink-soft">Numbers already used by members entered from the paper register are skipped automatically. Set the next value to continue after the last paper number.</p>
          {msg && <div className="mb-3"><Alert tone={msg.tone}>{msg.text}</Alert></div>}
          <div className="flex items-end gap-2">
            <TextField label="Set next sequence value" type="number" min={1} value={next} onChange={(e) => setNext(e.target.value)} wrapperClassName="flex-1" />
            <Button variant="secondary" disabled={!next || Number(next) < 1} onClick={() => setConfirm(true)}>Update</Button>
          </div>
        </Panel>
        <Panel title="Rules">
          <div className="register">
            <RegisterRows rows={[
              { label: "Minimum age", value: `${data.rules.minimum_age_years} years` },
              { label: "Editing window", value: `${data.rules.edit_permission_hours} hours` },
              { label: "Introducer signature required", value: yes(data.rules.require_introducer_signature) },
              { label: "Introducer must be in the register", value: yes(data.rules.introducer_must_be_registered) },
              { label: "Verified email and mobile before submitting", value: yes(data.rules.require_verified_contact_for_submission) },
              { label: "Email provider", value: data.providers.email },
              { label: "SMS provider", value: data.providers.sms },
              { label: "Environment", value: data.environment },
            ]} />
          </div>
        </Panel>
        <Panel title="Organisation" className="lg:col-span-2">
          <div className="register">
            <RegisterRows rows={Object.entries(data.organisation).map(([k, v]) => ({ label: k.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase()), value: v }))} />
          </div>
        </Panel>
      </div>
      <ConfirmDialog open={confirm} title="Change the membership sequence?" confirmLabel="Update sequence" loading={busy} onConfirm={save} onCancel={() => setConfirm(false)}>
        <p>The next automatically generated number will be based on {next}. Existing members keep their numbers. This change is recorded in the audit log.</p>
      </ConfirmDialog>
    </>
  );
}
