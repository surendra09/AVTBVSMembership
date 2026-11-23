import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Download, UserPlus, Users } from "lucide-react";
import { ButtonLink, buttonClass } from "@/components/ui/Button";
import { Avatar, PageHeader, Pagination, SearchInput, Table } from "@/components/ui/Data";
import { EmptyState, ErrorState, Loading, StatusBadge } from "@/components/ui/Feedback";
import { SelectField } from "@/components/ui/Form";
import { useApi, useDebounced } from "@/hooks/useApi";
import type { AdminMemberListItem, Page } from "@/types";
import { formatDate } from "@/utils/format";

export default function MembersPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [city, setCity] = useState("");
  const status = params.get("status") ?? "";
  const source = params.get("source") ?? "";
  const sort = params.get("sort") ?? "name";
  const [page, setPage] = useState(1);
  const dq = useDebounced(q);
  const dcity = useDebounced(city);
  const { data, loading, error, reload } = useApi<Page<AdminMemberListItem>>("/admin/members", {
    q: dq || undefined, city: dcity || undefined, status: status || undefined, source: source || undefined, sort, page, page_size: 20,
  });
  const setParam = (k: string, v: string) => { const p = new URLSearchParams(params); if (v) p.set(k, v); else p.delete(k); setParams(p); setPage(1); };

  return (
    <>
      <PageHeader title="All members" description="Every official member, whether approved online or entered from the paper register."
        actions={<>
          <a className={buttonClass("secondary")} href={`/api/admin/reports/members.csv${status ? `?status=${status}` : ""}`}><Download className="h-4 w-4" /> Export CSV</a>
          <ButtonLink to="/admin/members/new"><UserPlus className="h-4 w-4" /> Add existing member</ButtonLink>
        </>} />
      <div className="mb-4 grid gap-3 md:grid-cols-[1fr_11rem_10rem_12rem_12rem]">
        <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Name, father's name, membership no. or mobile" />
        <label><span className="sr-only">City</span><input className="field-input" placeholder="City" value={city} onChange={(e) => { setCity(e.target.value); setPage(1); }} /></label>
        <SelectField label="Status" wrapperClassName="[&>label]:sr-only" value={status} onChange={(e) => setParam("status", e.target.value)}
          options={[{ value: "", label: "Any status" }, { value: "ACTIVE", label: "Active" }, { value: "INACTIVE", label: "Inactive" }]} />
        <SelectField label="Source" wrapperClassName="[&>label]:sr-only" value={source} onChange={(e) => setParam("source", e.target.value)}
          options={[{ value: "", label: "Any source" }, { value: "ONLINE_APPLICATION", label: "Applied online" }, { value: "MANUAL_ENTRY", label: "Entered by office" }]} />
        <SelectField label="Sort" wrapperClassName="[&>label]:sr-only" value={sort} onChange={(e) => setParam("sort", e.target.value)}
          options={[{ value: "name", label: "Sort by name" }, { value: "number", label: "Sort by number" }, { value: "recent", label: "Newest first" }]} />
      </div>
      {loading && !data ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data && data.items.length === 0 ? (
        <EmptyState title="No members found" icon={<Users className="h-6 w-6" />}
          action={<ButtonLink to="/admin/members/new" variant="secondary">Add an existing member</ButtonLink>}>
          {dq || status || source || dcity ? "Try clearing the filters." : "Approve applications or add existing members from the paper register."}
        </EmptyState>
      ) : data && (
        <>
          <Table caption="Members" rows={data.items} rowKey={(r) => r.id} onRowClick={(r) => navigate(`/admin/members/${r.id}`)} columns={[
            { key: "no", header: "Mem. no.", render: (r) => <span className="font-display text-register">{r.membership_number}</span> },
            { key: "name", header: "Member", render: (r) => (
              <span className="flex items-center gap-3"><Avatar src={r.photo_url} name={r.full_name} size={36} />
                <span><span className="block font-medium">{r.full_name}</span><span className="block text-sm text-ink-muted">S/o {r.father_name}</span></span></span>) },
            { key: "city", header: "City", render: (r) => r.city },
            { key: "cell", header: "Cell", render: (r) => r.cell },
            { key: "src", header: "Source", render: (r) => <span className="text-sm text-ink-soft">{r.source === "MANUAL_ENTRY" ? "Office entry" : "Online"}{r.has_account ? "" : ", no login"}</span> },
            { key: "since", header: "Enrolled", render: (r) => formatDate(r.enrolled_at) },
            { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
          ]} />
          <Pagination page={data.page} pages={data.pages} total={data.total} onPage={setPage} noun="members" />
        </>
      )}
    </>
  );
}
