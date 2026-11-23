import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Inbox } from "lucide-react";
import { Avatar, PageHeader, Pagination, SearchInput, Table, Tabs } from "@/components/ui/Data";
import { EmptyState, ErrorState, Loading, StatusBadge } from "@/components/ui/Feedback";
import { SelectField } from "@/components/ui/Form";
import { useApi, useDebounced } from "@/hooks/useApi";
import type { ApplicationListItem, ApplicationStatus, Page } from "@/types";
import { formatDate } from "@/utils/format";

const VIEWS: Record<string, { label: string; statuses?: ApplicationStatus[] }> = {
  all: { label: "All" },
  pending: { label: "Pending", statuses: ["PENDING", "RESUBMITTED"] },
  corrections: { label: "Correction requests", statuses: ["CORRECTION_REQUIRED"] },
  approved: { label: "Approved", statuses: ["APPROVED"] },
  rejected: { label: "Rejected", statuses: ["REJECTED"] },
};

export default function ApplicationsPage() {
  const params = useParams();
  const view = params.view ?? params.id ?? "all";
  const navigate = useNavigate();
  const current = VIEWS[view] ?? VIEWS.all;
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("submitted_asc");
  const [page, setPage] = useState(1);
  const dq = useDebounced(q);
  const { data, loading, error, reload } = useApi<Page<ApplicationListItem>>("/admin/applications", {
    status: current.statuses, q: dq || undefined, sort, page, page_size: 20,
  });

  return (
    <>
      <PageHeader title="Membership applications" description="Open an application to verify the details and documents." />
      <Tabs value={view in VIEWS ? view : "all"} onChange={(v) => { setPage(1); navigate(`/admin/applications${v === "all" ? "" : `/${v}`}`); }}
        options={Object.entries(VIEWS).map(([value, v]) => ({ value, label: v.label }))} />
      <div className="my-4 grid gap-3 sm:grid-cols-[1fr_15rem]">
        <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Name, father's name, application no., mobile or introducer no." />
        <SelectField label="Sort" wrapperClassName="[&>label]:sr-only" value={sort} onChange={(e) => setSort(e.target.value)} options={[
          { value: "submitted_asc", label: "Oldest submission first" }, { value: "submitted_desc", label: "Newest submission first" },
          { value: "name", label: "Name A–Z" }, { value: "updated_desc", label: "Recently updated" }]} />
      </div>
      {loading && !data ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data && data.items.length === 0 ? (
        <EmptyState title="No applications here" icon={<Inbox className="h-6 w-6" />}>{dq ? "Nothing matches your search." : "Applications in this list will appear as members of the public apply."}</EmptyState>
      ) : data && (
        <>
          <Table caption="Applications" rows={data.items} rowKey={(r) => r.id} onRowClick={(r) => navigate(`/admin/applications/${r.id}`)} columns={[
            { key: "name", header: "Applicant", render: (r) => (
              <span className="flex items-center gap-3"><Avatar src={r.photo_url} name={r.full_name ?? "?"} size={36} />
                <span><span className="block font-medium">{r.full_name || "(no name yet)"}</span><span className="block text-sm text-ink-muted">S/o {r.father_name || "—"}</span></span></span>) },
            { key: "no", header: "Application no.", render: (r) => <span className="text-sm">{r.application_number}</span> },
            { key: "city", header: "City", render: (r) => r.city || "—" },
            { key: "intro", header: "Introducer no.", render: (r) => r.introducer_reg_no || "—" },
            { key: "sub", header: "Submitted", render: (r) => formatDate(r.last_submitted_at) },
            { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
          ]} />
          <Pagination page={data.page} pages={data.pages} total={data.total} onPage={setPage} noun="applications" />
        </>
      )}
    </>
  );
}
