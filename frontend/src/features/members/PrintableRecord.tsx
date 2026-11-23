import type { FormData as MemberFormData, OfficeUse } from "@/types";
import { usePublicConfig } from "@/hooks/usePublicConfig";
import { formatDate } from "@/utils/format";

interface Props {
  data: MemberFormData & { membership_number: string; enrolled_at: string; declaration_place: string | null; declaration_date: string | null };
  photoUrl: string | null;
  office?: Partial<OfficeUse>;
  aadhaar?: string | null;
}

/** Printable membership record laid out like the official paper form. */
export function PrintableRecord({ data: d, photoUrl, office, aadhaar }: Props) {
  const { organisation: o } = usePublicConfig();
  const cell = "border border-register/60 px-2 py-1.5 align-top";
  const label = `${cell} w-[24%] text-[13px] text-register`;
  return (
    <article className="mx-auto max-w-[780px] bg-white p-6 text-[14px] text-ink print:p-0">
      <header className="mb-3 text-center">
        <img src="/brand/emblem-192.png" alt="" className="mx-auto mb-1 h-16" />
        <p className="font-display text-xl text-register">{o.full_name} ({o.registration})</p>
        <p className="font-display text-lg text-register" lang="te">{o.telugu_name}</p>
        <p className="text-[13px]">Formerly known as {o.formerly_known_as}</p>
        <p className="text-[13px]">{o.address}</p>
        <p className="text-[13px]">Ph: {o.phone}, Email: {o.email}</p>
      </header>
      <table className="w-full border-collapse">
        <tbody>
          <tr>
            <td className={`${cell} text-center font-display text-lg text-register`} colSpan={3}>Life Membership Record</td>
            <td className={`${cell} w-[22%] text-center`} rowSpan={5}>
              {photoUrl ? <img src={photoUrl} alt="Member photograph" className="mx-auto h-36 w-28 object-cover" /> : <span className="text-[12px] text-ink-muted">Photograph</span>}
            </td>
          </tr>
          <tr><td className={label}>Name</td><td className={cell} colSpan={2}>{d.full_name}</td></tr>
          <tr><td className={label}>Father's Name</td><td className={cell} colSpan={2}>{d.father_name}</td></tr>
          <tr><td className={label}>Address</td><td className={cell} colSpan={2}>{[d.address_line1, d.address_line2].filter(Boolean).join(", ")}</td></tr>
          <tr><td className={label}>City/Town/Village</td><td className={cell} colSpan={2}>{d.city}, {d.state}, {d.country}</td></tr>
          <tr><td className={label}>Pincode</td><td className={cell}>{d.pincode}</td><td className={label}>D.O.B.</td><td className={cell}>{d.date_of_birth ? formatDate(d.date_of_birth) : ""}</td></tr>
          <tr><td className={label}>Aadhar Card No.</td><td className={cell}>{aadhaar ?? d.aadhaar_masked ?? ""}</td><td className={label}>Blood Group</td><td className={cell}>{d.blood_group}</td></tr>
          <tr><td className={label}>Phone</td><td className={cell}>{d.phone}</td><td className={label}>Centre X No.</td><td className={cell}>{d.centre_x_no}</td></tr>
          <tr><td className={label}>Cell</td><td className={cell}>{d.cell}</td><td className={label}>Whatsapp/Face Book</td><td className={cell}>{d.whatsapp_facebook}</td></tr>
          <tr><td className={label}>E.Mail</td><td className={cell} colSpan={3}>{d.email}</td></tr>
          <tr><td className={label}>Family Surname</td><td className={cell}>{d.family_surname}</td><td className={label}>Gothram / Natchathiram</td><td className={cell}>{[d.gothram, d.natchathiram].filter(Boolean).join(" / ")}</td></tr>
          <tr><td className={label}>Occupation</td><td className={cell} colSpan={3}>{d.occupation}</td></tr>
          <tr><td className={label}>Address</td><td className={cell} colSpan={3}>{d.occupation_address}</td></tr>
          <tr><td className={label}>Native Place Address</td><td className={cell} colSpan={3}>{d.native_place_address}</td></tr>
          <tr><td className={label}>Introduced by Sri</td><td className={cell}>{d.introducer_name}</td><td className={label}>Reg. No.</td><td className={cell}>{d.introducer_reg_no}</td></tr>
          <tr><td className={label}>Introducer Phone No.</td><td className={cell} colSpan={3}>{d.introducer_phone}</td></tr>
          <tr>
            <td className={`${cell} py-3`} colSpan={4}>
              I {d.full_name} S/o {d.father_name} declare that I have completed 18 years and belong to <strong>{o.community_name}</strong>. I assure that I agree abide by the rules and regulations of the Sabha.
              <div className="mt-3 flex justify-between"><span>Place: {d.declaration_place}</span><span>Date: {d.declaration_date ? formatDate(d.declaration_date) : ""}</span><span>Signature of Applicant</span></div>
            </td>
          </tr>
          <tr><td className={`${cell} font-medium text-register`}>For Office Use Only</td><td className={cell}>Verified by: {office?.verified_by}</td><td className={label}>Rec. No. / Date</td><td className={cell}>{office?.receipt_number} {office?.receipt_date ? `/ ${formatDate(office.receipt_date)}` : ""}</td></tr>
          <tr>
            <td className={cell} colSpan={2}>
              Membership Enrollment Committee, for AVTBV Sabha
              <div className="mt-6 grid grid-cols-3 gap-2 text-center text-[13px]">
                <span>{office?.committee_chairman}<br />Chairman</span><span>{office?.committee_secretary}<br />Secretary</span><span>{office?.committee_president}<br />President</span>
              </div>
            </td>
            <td className={label}>Regd. Mem. No.</td>
            <td className={`${cell} font-display text-2xl text-register`}>{d.membership_number}<div className="text-[12px] text-ink-muted">Enrolled {formatDate(d.enrolled_at)}</div></td>
          </tr>
        </tbody>
      </table>
    </article>
  );
}
