import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Mail, MapPin, Phone, Users } from "lucide-react";
import { Avatar, PageHeader, Pagination, RegisterRows, SearchInput } from "@/components/ui/Data";
import { EmptyState, ErrorState, Loading } from "@/components/ui/Feedback";
import { SelectField } from "@/components/ui/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { PublicDirectoryList } from "@/features/members/PublicDirectoryList";
import { useApi, useDebounced } from "@/hooks/useApi";
import type { DirectoryMember, Page } from "@/types";
import { formatDate } from "@/utils/format";

/** Full directory for approved members; non-members see the public register only. */
export default function MemberDirectoryPage() {
  const { me } = useAuth();
  const allowed = me?.membership.is_member || me?.user.role !== "USER";
  if (!allowed) {
    return (
      <>
        <PageHeader title="Member directory" description="Full member details become visible once your membership is approved. Until then you can search names and fathers' names." />
        <PublicDirectoryList pageSize={25} />
      </>
    );
  }
  return <FullDirectory />;
}

function FullDirectory() {
  const [q, setQ] = useState("");
  const [city, setCity] = useState("");
  const [sort, setSort] = useState("name");
  const [page, setPage] = useState(1);
  const dq = useDebounced(q);
  const dcity = useDebounced(city);
  const { data, loading, error, reload } = useApi<Page<DirectoryMember>>("/members", { q: dq || undefined, city: dcity || undefined, sort, page, page_size: 24 });

  return (
    <>
      <PageHeader title="Member directory" description="Details are shared only with approved members. Please use them for Sabha matters only." />
      <div className="mb-5 grid gap-3 sm:grid-cols-[1fr_14rem_12rem]">
        <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Name, father's name or membership no." />
        <label className="block"><span className="sr-only">Filter by city</span>
          <input value={city} onChange={(e) => { setCity(e.target.value); setPage(1); }} placeholder="City/Town/Village" className="field-input" />
        </label>
        <SelectField label="Sort" className="!mt-0" wrapperClassName="[&>label]:sr-only" value={sort} onChange={(e) => setSort(e.target.value)}
          options={[{ value: "name", label: "Sort by name" }, { value: "number", label: "Sort by membership no." }, { value: "recent", label: "Newest members" }, { value: "city", label: "Sort by city" }]} />
      </div>
      {loading && !data ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data && data.items.length === 0 ? (
        <EmptyState title="No members found" icon={<Users className="h-6 w-6" />}>Try a different spelling, or clear the city filter.</EmptyState>
      ) : data && (
        <>
          <ul className="grid gap-3 md:grid-cols-2">
            {data.items.map((m) => (
              <li key={m.id}>
                <Link to={`/dashboard/directory/${m.id}`} className="flex gap-4 border border-line bg-white p-4 hover:border-forest/40">
                  <Avatar src={m.photo_url} name={m.full_name} size={64} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-display text-lg leading-snug text-forest">{m.full_name}</p>
                      <span className="shrink-0 text-sm text-register">No. {m.membership_number}</span>
                    </div>
                    <p className="text-[15px] text-ink-soft">S/o {m.father_name}</p>
                    <p className="mt-1 flex items-center gap-1.5 text-sm text-ink-muted"><MapPin className="h-3.5 w-3.5" />{m.city}, {m.state}</p>
                    {m.cell && <p className="flex items-center gap-1.5 text-sm text-ink-muted"><Phone className="h-3.5 w-3.5" />{m.cell}</p>}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
          <Pagination page={data.page} pages={data.pages} total={data.total} onPage={setPage} noun="members" />
        </>
      )}
    </>
  );
}

export function MemberProfilePage() {
  const { id } = useParams();
  const { data: m, loading, error, reload } = useApi<DirectoryMember>(`/members/${id}`);
  if (loading && !m) return <Loading />;
  if (error || !m) return <ErrorState message={error ?? "Member not found"} onRetry={reload} />;
  const address = [m.address_line1, m.address_line2, m.city, m.state, m.pincode].filter(Boolean).join(", ");
  return (
    <>
      <Link to="/dashboard/directory" className="mb-4 inline-block text-[15px] text-forest underline decoration-forest/30">Back to directory</Link>
      <div className="mb-6 flex flex-wrap items-center gap-6 border border-line bg-white p-5">
        <Avatar src={m.photo_url} name={m.full_name} size={112} />
        <div className="min-w-0 flex-1">
          <h1 className="text-3xl">{m.full_name}</h1>
          <p className="text-ink-soft">S/o {m.father_name}</p>
          <p className="mt-1 text-sm text-ink-muted">Member since {formatDate(m.enrolled_at)}</p>
        </div>
        <div className="reg-stamp"><span className="text-[12px]">Regd. Mem. No.</span><span className="font-display text-2xl">{m.membership_number}</span></div>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="register">
          <div className="register-section">Contact</div>
          <RegisterRows rows={m.cell === null && m.email === null ? [{ label: "Contact", value: <span className="text-ink-muted">This member has chosen not to share contact details.</span> }] : [
            { label: "Cell", value: m.cell && <a className="text-forest underline" href={`tel:${m.cell}`}>{m.cell}</a> },
            { label: "Phone", value: m.phone },
            { label: "E-mail", value: m.email && <a className="inline-flex items-center gap-1 text-forest underline" href={`mailto:${m.email}`}><Mail className="h-3.5 w-3.5" />{m.email}</a> },
            { label: "WhatsApp/Facebook", value: m.whatsapp_facebook },
          ]} />
          <div className="register-section">Address</div>
          <RegisterRows rows={m.address_line1 ? [
            { label: "Address", value: address }, { label: "Country", value: m.country },
            { label: "Occupation address", value: m.occupation_address },
          ] : [{ label: "Address", value: <span className="text-ink-muted">{m.city}, {m.state} (full address not shared)</span> }]} />
        </div>
        <div className="register">
          <div className="register-section">Family and occupation</div>
          <RegisterRows rows={[
            { label: "Family surname", value: m.family_surname }, { label: "Gothram", value: m.gothram },
            { label: "Natchathiram", value: m.natchathiram }, { label: "Blood group", value: m.blood_group },
            { label: "Occupation", value: m.occupation }, { label: "Native place", value: m.native_place_address },
          ]} />
        </div>
      </div>
    </>
  );
}
