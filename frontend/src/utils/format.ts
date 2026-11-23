import type { ApplicationStatus, DocumentType } from "@/types";

const dateFmt = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" });
const dateTimeFmt = new Intl.DateTimeFormat("en-IN", {
  day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit",
});

export const formatDate = (v?: string | null) => (v ? dateFmt.format(new Date(v)) : "—");
export const formatDateTime = (v?: string | null) => (v ? dateTimeFmt.format(new Date(v)) : "—");

export function timeRemaining(until: string | null | undefined, now = Date.now()): string {
  if (!until) return "";
  const ms = new Date(until).getTime() - now;
  if (ms <= 0) return "expired";
  const h = Math.floor(ms / 3_600_000);
  const m = Math.floor((ms % 3_600_000) / 60_000);
  return h > 0 ? `${h} h ${m} min left` : `${m} min left`;
}

export const STATUS_LABEL: Record<ApplicationStatus, string> = {
  DRAFT: "Draft",
  PENDING: "Awaiting verification",
  CORRECTION_REQUIRED: "Corrections requested",
  RESUBMITTED: "Resubmitted",
  APPROVED: "Approved",
  REJECTED: "Not approved",
};

export const DOC_LABEL: Record<DocumentType, string> = {
  PHOTO: "Recent passport-size photograph",
  ID_PROOF: "Identity proof",
  ADDITIONAL_PHOTO_1: "Additional passport-size photograph (1)",
  ADDITIONAL_PHOTO_2: "Additional passport-size photograph (2)",
  INTRODUCER_SIGNATURE: "Introducer's signature",
  APPLICANT_SIGNATURE: "Signature of applicant",
};

export const HISTORY_LABEL: Record<string, string> = {
  CREATED: "Application started",
  SUBMITTED: "Submitted for verification",
  CORRECTION_REQUESTED: "Corrections requested",
  RESUBMITTED: "Resubmitted after corrections",
  APPROVED: "Approved",
  REJECTED: "Not approved",
};

export const FIELD_LABEL: Record<string, string> = {
  full_name: "Name", father_name: "Father's name", address_line1: "Address", address_line2: "Address (line 2)",
  city: "City/Town/Village", state: "State", country: "Country", pincode: "Pincode", aadhaar_number: "Aadhaar card no.",
  blood_group: "Blood group", date_of_birth: "Date of birth", phone: "Phone", centre_x_no: "Centre X No.",
  cell: "Cell", email: "E-mail", whatsapp_facebook: "WhatsApp/Facebook", family_surname: "Family surname",
  gothram: "Gothram", natchathiram: "Natchathiram", occupation: "Occupation", occupation_address: "Occupation address",
  native_place_address: "Native place address", introducer_name: "Introduced by Sri",
  introducer_phone: "Introducer phone no.", introducer_reg_no: "Introducer reg. no.",
  show_contact_in_directory: "Show contact in directory", show_address_in_directory: "Show address in directory",
  declaration_accepted: "Declaration", declaration_place: "Place", declaration_date: "Date", status: "Status",
  linked_account: "Linked account",
};

export const fieldLabel = (key: string) => {
  if (key.startsWith("office:")) return `Office: ${key.slice(7).replace(/_/g, " ")}`;
  if (key.startsWith("document:")) return DOC_LABEL[key.slice(9) as DocumentType] ?? key;
  return FIELD_LABEL[key] ?? key.replace(/_/g, " ");
};

export const initials = (name: string) =>
  name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join("");

export const bytes = (n: number) => (n > 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.round(n / 1024)} KB`);
