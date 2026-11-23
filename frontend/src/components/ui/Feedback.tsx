import type { ReactNode } from "react";
import { AlertCircle, CheckCircle2, Info, TriangleAlert } from "lucide-react";
import type { ApplicationStatus, EditRequestStatus, MembershipStatus } from "@/types";
import { STATUS_LABEL } from "@/utils/format";

export function Spinner({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-12 text-ink-soft" role="status">
      <Spinner /> <span>{label}…</span>
    </div>
  );
}

type Tone = "info" | "success" | "warning" | "error";
const tones: Record<Tone, { cls: string; Icon: typeof Info }> = {
  info: { cls: "border-forest/25 bg-forest-50 text-forest", Icon: Info },
  success: { cls: "border-ok/30 bg-ok-bg text-ok", Icon: CheckCircle2 },
  warning: { cls: "border-caution/30 bg-caution-bg text-caution", Icon: TriangleAlert },
  error: { cls: "border-danger/30 bg-danger-bg text-danger", Icon: AlertCircle },
};

export function Alert({ tone = "info", title, children, action }: { tone?: Tone; title?: string; children?: ReactNode; action?: ReactNode }) {
  const { cls, Icon } = tones[tone];
  return (
    <div className={`flex gap-3 rounded border px-4 py-3 ${cls}`} role={tone === "error" ? "alert" : "status"}>
      <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1 text-[15px]">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className="whitespace-pre-line text-ink-soft [&_a]:underline">{children}</div>}
      </div>
      {action && <div className="shrink-0 self-center">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="py-8">
      <Alert tone="error" title="This couldn't be loaded" action={onRetry && (
        <button className="text-sm font-medium underline" onClick={onRetry}>Try again</button>
      )}>{message}</Alert>
    </div>
  );
}

export function EmptyState({ title, children, action, icon }: { title: string; children?: ReactNode; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-2 border border-dashed border-forest/25 bg-white/60 px-6 py-10">
      {icon && <div className="text-forest/60">{icon}</div>}
      <p className="font-display text-lg text-forest">{title}</p>
      {children && <div className="max-w-prose text-ink-soft">{children}</div>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

const statusStyle: Record<string, string> = {
  DRAFT: "bg-sage text-ink-soft",
  PENDING: "bg-champagne-100 text-caution",
  RESUBMITTED: "bg-champagne-100 text-caution",
  CORRECTION_REQUIRED: "bg-caution-bg text-caution",
  APPROVED: "bg-ok-bg text-ok",
  ACTIVE: "bg-ok-bg text-ok",
  REJECTED: "bg-danger-bg text-danger",
  INACTIVE: "bg-sage text-ink-muted",
  SENT: "bg-ok-bg text-ok",
  FAILED: "bg-danger-bg text-danger",
  SENDING: "bg-champagne-100 text-caution",
};

const otherLabels: Record<string, string> = {
  ACTIVE: "Active", INACTIVE: "Inactive", SENT: "Sent", FAILED: "Failed", SENDING: "Sending",
};

export function StatusBadge({ status, label }: { status: ApplicationStatus | MembershipStatus | EditRequestStatus | string; label?: string }) {
  const text = label ?? (STATUS_LABEL as Record<string, string>)[status] ?? otherLabels[status] ??
    status.charAt(0) + status.slice(1).toLowerCase();
  return (
    <span className={`inline-flex items-center rounded-sm px-2 py-0.5 text-[13px] font-medium ${statusStyle[status] ?? "bg-sage text-ink-soft"}`}>
      {text}
    </span>
  );
}
