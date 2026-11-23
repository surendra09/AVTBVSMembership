import { Download } from "lucide-react";
import { buttonClass } from "@/components/ui/Button";
import { PageHeader, Panel } from "@/components/ui/Data";
import { ErrorState, Loading } from "@/components/ui/Feedback";
import { useApi } from "@/hooks/useApi";
import { STATUS_LABEL } from "@/utils/format";
import type { ApplicationStatus } from "@/types";

interface Summary {
  new_members_by_month: { month: string; count: number }[];
  applications_by_status: Record<ApplicationStatus, number>;
  members_by_source: Record<string, number>;
  top_cities: { city: string; count: number }[];
  blood_groups: { blood_group: string; count: number }[];
}

function Bars({ rows, label }: { rows: { name: string; value: number }[]; label: string }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  if (!rows.length) return <p className="text-ink-soft">No data yet.</p>;
  return (
    <table className="w-full text-[15px]" aria-label={label}>
      <tbody>
        {rows.map((r) => (
          <tr key={r.name}>
            <th scope="row" className="w-36 py-1.5 pr-3 text-left font-normal text-ink-soft">{r.name}</th>
            <td className="py-1.5">
              <div className="flex items-center gap-2">
                <div className="h-3 rounded-sm bg-forest" style={{ width: `${(r.value / max) * 100}%`, minWidth: r.value ? 4 : 0 }} />
                <span className="text-sm text-ink">{r.value}</span>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function ReportsPage() {
  const { data, loading, error, reload } = useApi<Summary>("/admin/reports/summary", { months: 12 });
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? ""} onRetry={reload} />;
  const monthName = (m: string) => new Date(`${m}-01T00:00:00`).toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
  const maxMonth = Math.max(1, ...data.new_members_by_month.map((x) => x.count));
  return (
    <>
      <PageHeader title="Reports" description="Membership figures for the committee."
        actions={<>
          <a className={buttonClass("secondary")} href="/api/admin/reports/members.csv?status=ACTIVE"><Download className="h-4 w-4" /> Active members (CSV)</a>
          <a className={buttonClass("secondary")} href="/api/admin/reports/members.csv"><Download className="h-4 w-4" /> All members (CSV)</a>
        </>} />
      <Panel title="New members, last 12 months" className="mb-6">
        <div className="flex h-48 items-end gap-1.5 sm:gap-3" role="img" aria-label="New members per month">
          {data.new_members_by_month.map((m) => (
            <div key={m.month} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
              <span className="text-[12px] text-ink-soft">{m.count || ""}</span>
              <div className="w-full max-w-10 rounded-t-sm bg-forest" style={{ height: `${(m.count / maxMonth) * 80}%`, minHeight: m.count ? 3 : 1, opacity: m.count ? 1 : 0.15 }} />
              <span className="text-[11px] text-ink-muted">{monthName(m.month)}</span>
            </div>
          ))}
        </div>
      </Panel>
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Applications by status">
          <Bars label="Applications by status" rows={(Object.keys(STATUS_LABEL) as ApplicationStatus[]).map((s) => ({ name: STATUS_LABEL[s], value: data.applications_by_status[s] ?? 0 }))} />
        </Panel>
        <Panel title="How members joined">
          <Bars label="Members by source" rows={[{ name: "Applied online", value: data.members_by_source.ONLINE_APPLICATION ?? 0 }, { name: "Office entry", value: data.members_by_source.MANUAL_ENTRY ?? 0 }]} />
        </Panel>
        <Panel title="Active members by city (top 10)">
          <Bars label="Members by city" rows={data.top_cities.map((c) => ({ name: c.city, value: c.count }))} />
        </Panel>
        <Panel title="Active members by blood group">
          <Bars label="Members by blood group" rows={data.blood_groups.map((b) => ({ name: b.blood_group, value: b.count }))} />
        </Panel>
      </div>
    </>
  );
}
