import type { ReactNode } from "react";
import { FileText } from "lucide-react";
import { RegisterRows } from "@/components/ui/Data";
import type { DocumentItem, FormData as MemberFormData, HistoryItem } from "@/types";
import { DOC_LABEL, HISTORY_LABEL, formatDate, formatDateTime } from "@/utils/format";

const yesNo = (v: boolean) => (v ? "Shown to members" : "Hidden from members");

/** Read-only rendering of the official form, in the paper form's section order. */
export function FormDataView({ data, aadhaar, extra }: { data: MemberFormData; aadhaar?: ReactNode; extra?: ReactNode }) {
  return (
    <div className="register">
      <div className="register-section">Personal details</div>
      <RegisterRows rows={[
        { label: "Name", value: data.full_name },
        { label: "Father's name", value: data.father_name },
        { label: "Address", value: [data.address_line1, data.address_line2].filter(Boolean).join(", ") },
        { label: "City/Town/Village", value: data.city },
        { label: "State", value: data.state },
        { label: "Country", value: data.country },
        { label: "Pincode", value: data.pincode },
        { label: "Aadhaar card no.", value: aadhaar ?? data.aadhaar_masked },
        { label: "Date of birth", value: data.date_of_birth ? formatDate(data.date_of_birth) : null },
        { label: "Blood group", value: data.blood_group },
      ]} />
      <div className="register-section">Contact details</div>
      <RegisterRows rows={[
        { label: "Phone", value: data.phone },
        { label: "Centre X No.", value: data.centre_x_no },
        { label: "Cell", value: data.cell },
        { label: "E-mail", value: data.email },
        { label: "WhatsApp/Facebook", value: data.whatsapp_facebook },
      ]} />
      <div className="register-section">Family details</div>
      <RegisterRows rows={[
        { label: "Family surname", value: data.family_surname },
        { label: "Gothram", value: data.gothram },
        { label: "Natchathiram", value: data.natchathiram },
      ]} />
      <div className="register-section">Occupation and native place</div>
      <RegisterRows rows={[
        { label: "Occupation", value: data.occupation },
        { label: "Occupation address", value: data.occupation_address },
        { label: "Native place address", value: data.native_place_address },
      ]} />
      <div className="register-section">Introducer details</div>
      <RegisterRows rows={[
        { label: "Introduced by Sri", value: data.introducer_name },
        { label: "Introducer phone no.", value: data.introducer_phone },
        { label: "Introducer reg. no.", value: data.introducer_reg_no },
      ]} />
      <div className="register-section">Directory privacy</div>
      <RegisterRows rows={[
        { label: "Contact details", value: yesNo(data.show_contact_in_directory) },
        { label: "Address", value: yesNo(data.show_address_in_directory) },
      ]} />
      {extra}
    </div>
  );
}

export function DeclarationText({ name, father, community }: { name?: string | null; father?: string | null; community: string }) {
  // Exact wording of the declaration printed on the official form.
  return (
    <p className="font-display text-[17px] leading-relaxed text-ink">
      I <span className="border-b border-dotted border-ink-muted px-1">{name || "…………………"}</span> S/o{" "}
      <span className="border-b border-dotted border-ink-muted px-1">{father || "…………………"}</span> declare that I have completed 18 years
      and belong to <strong className="font-normal text-forest">{community}</strong>. I assure that I agree abide by the rules and
      regulations of the Sabha.
    </p>
  );
}

export function DocumentGallery({ documents }: { documents: DocumentItem[] }) {
  if (!documents.length) return <p className="text-ink-muted">No documents uploaded.</p>;
  return (
    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {documents.map((d) => (
        <li key={d.id} className="border border-line bg-white">
          <a href={d.url} target="_blank" rel="noreferrer" className="block">
            <div className="flex h-40 items-center justify-center overflow-hidden bg-ivory">
              {d.content_type.startsWith("image/") ? (
                <img src={d.url} alt={DOC_LABEL[d.doc_type]} className="h-full w-full object-contain" loading="lazy" />
              ) : (
                <span className="flex flex-col items-center gap-1 text-forest"><FileText className="h-10 w-10" /> <span className="text-sm">Open PDF</span></span>
              )}
            </div>
            <p className="border-t border-line px-3 py-2 text-sm text-ink">{DOC_LABEL[d.doc_type]}</p>
          </a>
        </li>
      ))}
    </ul>
  );
}

export function HistoryTimeline({ history }: { history: HistoryItem[] }) {
  return (
    <ol className="relative space-y-4 border-l border-forest/25 pl-5">
      {history.map((h) => (
        <li key={h.id} className="relative">
          <span className="absolute -left-[25px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-forest" aria-hidden="true" />
          <p className="font-medium text-ink">{HISTORY_LABEL[h.action] ?? h.action}</p>
          <p className="text-[13px] text-ink-muted">{formatDateTime(h.created_at)}{h.actor_name ? `, by ${h.actor_name}` : ""}</p>
          {h.note && <p className="mt-1 whitespace-pre-line text-[15px] text-ink-soft">{h.note}</p>}
        </li>
      ))}
    </ol>
  );
}
