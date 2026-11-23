import { useParams } from "react-router-dom";
import { Printer } from "lucide-react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { ErrorState, Loading } from "@/components/ui/Feedback";
import { PrintableRecord } from "@/features/members/PrintableRecord";
import { useApi } from "@/hooks/useApi";
import type { AdminMember, MyMembership } from "@/types";

function Toolbar({ back }: { back: string }) {
  return (
    <div className="no-print mb-4 flex justify-between gap-2">
      <ButtonLink variant="quiet" to={back}>Back</ButtonLink>
      <Button onClick={() => window.print()}><Printer className="h-4 w-4" /> Print</Button>
    </div>
  );
}

export function MyPrintPage() {
  const { data, loading, error, reload } = useApi<MyMembership>("/members/me");
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? "Not found"} onRetry={reload} />;
  return (
    <>
      <Toolbar back="/dashboard/membership" />
      <PrintableRecord data={data} photoUrl={data.photo_url} />
    </>
  );
}

export function AdminPrintPage() {
  const { id } = useParams();
  const { data, loading, error, reload } = useApi<AdminMember>(`/admin/members/${id}`);
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? "Not found"} onRetry={reload} />;
  return (
    <>
      <Toolbar back={`/admin/members/${id}`} />
      <PrintableRecord data={data} photoUrl={data.photo_url} office={data} aadhaar={data.aadhaar_masked} />
    </>
  );
}
