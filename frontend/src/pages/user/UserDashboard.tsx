import { useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Mail, Smartphone } from "lucide-react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Data";
import { Alert, StatusBadge } from "@/components/ui/Feedback";
import { useAuth } from "@/features/auth/AuthContext";
import { api, parseApiError } from "@/services/api";
import type { Me } from "@/types";
import { timeRemaining } from "@/utils/format";

function VerifyContact({ channel }: { channel: "email" | "phone" }) {
  const { me, setMe } = useAuth();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ tone: "error" | "success"; text: string } | null>(null);
  const target = channel === "email" ? me?.user.email : me?.user.phone;
  const Icon = channel === "email" ? Mail : Smartphone;

  async function verify(e: React.FormEvent) {
    e.preventDefault();
    if (!/^\d{6}$/.test(code)) return setMsg({ tone: "error", text: "Enter the 6-digit code." });
    setBusy(true);
    setMsg(null);
    try {
      const { data } = await api.post<Me>(`/auth/verify-${channel}`, { code });
      setMe(data);
    } catch (err) {
      setMsg({ tone: "error", text: parseApiError(err).message });
    } finally {
      setBusy(false);
    }
  }
  async function resend() {
    setMsg(null);
    try {
      const { data } = await api.post<{ message: string }>("/auth/resend-otp", { channel });
      setMsg({ tone: "success", text: data.message });
    } catch (err) {
      setMsg({ tone: "error", text: parseApiError(err).message });
    }
  }

  return (
    <form onSubmit={verify} className="border border-line bg-white p-4">
      <p className="flex items-center gap-2 font-medium"><Icon className="h-4 w-4 text-forest" /> Verify your {channel === "email" ? "email address" : "mobile number"}</p>
      <p className="mt-0.5 text-sm text-ink-soft">Enter the code we sent to {target}.</p>
      <div className="mt-3 flex gap-2">
        <label className="sr-only" htmlFor={`otp-${channel}`}>Verification code</label>
        <input id={`otp-${channel}`} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
          inputMode="numeric" autoComplete="one-time-code" placeholder="6-digit code" className="field-input w-40 tracking-[0.3em] placeholder:tracking-normal" />
        <Button type="submit" loading={busy}>Verify</Button>
      </div>
      {import.meta.env.DEV && (
        <p className="mt-2 text-xs text-ink-soft">Demo mode: use code <span className="font-mono font-semibold">123456</span>.</p>
      )}
      {msg && <p className={`mt-2 text-sm ${msg.tone === "error" ? "text-danger" : "text-ok"}`}>{msg.text}</p>}
      <button type="button" onClick={resend} className="mt-2 text-sm text-forest underline decoration-forest/30">Send a new code</button>
    </form>
  );
}

export default function UserDashboard() {
  const { me } = useAuth();
  if (!me) return null;
  const { user, membership: m } = me;
  const verified = user.email_verified && user.phone_verified;
  const firstName = user.full_name.split(" ")[0];

  return (
    <div className="space-y-6">
      <div>
        <h1>Welcome, {firstName}</h1>
        <p className="mt-1 text-ink-soft">{m.is_member ? "You are a life member of the Sabha." : "Your account is ready. Membership begins once the committee approves your application."}</p>
      </div>

      {!verified && (
        <section aria-labelledby="verify-h" className="space-y-3">
          <h2 id="verify-h" className="text-lg">Confirm your contact details</h2>
          <div className="grid gap-3 md:grid-cols-2">
            {!user.email_verified && <VerifyContact channel="email" />}
            {!user.phone_verified && <VerifyContact channel="phone" />}
          </div>
        </section>
      )}

      {m.is_member && m.membership_number ? (
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <Panel>
            <p className="text-sm text-ink-soft">Registered membership number</p>
            <div className="reg-stamp mt-3">
              <span className="text-[12px]">Regd. Mem. No.</span>
              <span className="font-display text-3xl leading-tight">{m.membership_number}</span>
            </div>
            <div className="mt-5 flex items-center gap-3">
              <span className="text-ink-soft">Status</span> <StatusBadge status={m.membership_status ?? "ACTIVE"} />
            </div>
            {m.edit_permission_expires_at && (
              <div className="mt-4">
                <Alert tone="info" title="You can edit your details now" action={<ButtonLink size="sm" to="/dashboard/membership/edit">Edit details</ButtonLink>}>
                  Editing access ends in {timeRemaining(m.edit_permission_expires_at)}.
                </Alert>
              </div>
            )}
          </Panel>
          <Panel title="Quick links">
            <ul className="divide-y divide-line">
              <li className="py-2.5"><Link className="text-forest hover:underline" to="/dashboard/membership">My membership details</Link></li>
              <li className="py-2.5"><Link className="text-forest hover:underline" to="/dashboard/directory">Member directory</Link></li>
              <li className="py-2.5"><Link className="text-forest hover:underline" to="/dashboard/membership#edit-request">Request a change to my details</Link></li>
              <li className="py-2.5"><Link className="text-forest hover:underline" to="/dashboard/membership/print">Print my membership record</Link></li>
            </ul>
          </Panel>
        </div>
      ) : m.membership_number && m.membership_status === "INACTIVE" ? (
        <Alert tone="warning" title={`Membership ${m.membership_number} is inactive`}>Please contact the Sabha office for details.</Alert>
      ) : (
        <Panel title="Your membership application">
          {!m.application_status ? (
            <div className="space-y-3">
              <p className="text-ink-soft">You haven't started an application yet. It takes about 15 minutes if you have your photographs and introducer's details ready.</p>
              <ButtonLink to="/dashboard/application">Start the application</ButtonLink>
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <StatusBadge status={m.application_status} />
                <span className="text-ink-soft">
                  {m.application_status === "DRAFT" && "Your draft is saved. Finish and submit it when ready."}
                  {(m.application_status === "PENDING" || m.application_status === "RESUBMITTED") && "The committee is verifying your details."}
                  {m.application_status === "CORRECTION_REQUIRED" && "The office has asked you to correct some details."}
                  {m.application_status === "REJECTED" && "Your application was not approved."}
                </span>
              </div>
              <ButtonLink to="/dashboard/application" variant={m.application_status === "CORRECTION_REQUIRED" || m.application_status === "DRAFT" ? "primary" : "secondary"}>
                {m.application_status === "DRAFT" ? "Continue application" : m.application_status === "CORRECTION_REQUIRED" ? "Make corrections" : "View application"}
              </ButtonLink>
            </div>
          )}
        </Panel>
      )}

      {verified && !m.is_member && (
        <p className="flex items-center gap-2 text-sm text-ok"><CheckCircle2 className="h-4 w-4" /> Email address and mobile number verified.</p>
      )}
    </div>
  );
}
