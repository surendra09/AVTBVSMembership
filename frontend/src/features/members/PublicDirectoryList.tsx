import { useState } from "react";
import { Users } from "lucide-react";
import { SearchInput, Pagination } from "@/components/ui/Data";
import { EmptyState, ErrorState, Loading } from "@/components/ui/Feedback";
import { useApi, useDebounced } from "@/hooks/useApi";
import type { Page, PublicMember } from "@/types";

/**
 * Public register view. The API endpoint returns ONLY name and father's name,
 * so nothing private can reach this component.
 */
export function PublicDirectoryList({ pageSize = 20, initialQuery = "" }: { pageSize?: number; initialQuery?: string }) {
  const [q, setQ] = useState(initialQuery);
  const [page, setPage] = useState(1);
  const dq = useDebounced(q);
  const { data, loading, error, reload } = useApi<Page<PublicMember>>("/members/public", { q: dq || undefined, page, page_size: pageSize });

  return (
    <div>
      <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} label="Search members by name or father's name"
        placeholder="Search by name or father's name" />
      <div className="mt-4">
        {loading && !data ? <Loading label="Loading the register" /> : error ? <ErrorState message={error} onRetry={reload} /> :
          data && data.items.length === 0 ? (
            <EmptyState title={dq ? `No member matches “${dq}”` : "The register is empty"} icon={<Users className="h-6 w-6" />}>
              {dq ? "Check the spelling, or search with the father's name instead." : "Members will appear here once their membership is approved."}
            </EmptyState>
          ) : data && (
            <>
              <ol className="register divide-y divide-forest/15" aria-label="Members">
                <li className="hidden grid-cols-2 bg-forest-50 px-4 py-2 text-sm font-semibold text-forest sm:grid" aria-hidden="true">
                  <span>Name</span><span>Father's name</span>
                </li>
                {data.items.map((m) => (
                  <li key={m.id} className="grid gap-0.5 px-4 py-2.5 sm:grid-cols-2 sm:gap-4">
                    <span className="font-medium text-ink">{m.full_name}</span>
                    <span className="text-ink-soft"><span className="text-ink-muted sm:hidden">S/o </span>{m.father_name}</span>
                  </li>
                ))}
              </ol>
              <Pagination page={data.page} pages={data.pages} total={data.total} onPage={setPage} noun="members" />
            </>
          )}
      </div>
    </div>
  );
}
