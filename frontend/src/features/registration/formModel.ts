import type { FieldValues, Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { FormData as MemberFormData } from "@/types";
import { ageOn, isValidAadhaar, isValidPincode } from "@/utils/validation";

/** Form values as edited in the browser (strings for inputs, booleans for checkboxes). */
export interface FormValues {
  full_name: string;
  father_name: string;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  country: string;
  pincode: string;
  aadhaar_number: string;
  blood_group: string;
  date_of_birth: string;
  phone: string;
  centre_x_no: string;
  cell: string;
  email: string;
  whatsapp_facebook: string;
  family_surname: string;
  gothram: string;
  natchathiram: string;
  occupation: string;
  occupation_address: string;
  native_place_address: string;
  introducer_name: string;
  introducer_phone: string;
  introducer_reg_no: string;
  show_contact_in_directory: boolean;
  show_address_in_directory: boolean;
  declaration_accepted: boolean;
  declaration_place: string;
  declaration_date: string;
}

export const TEXT_FIELDS = [
  "full_name", "father_name", "address_line1", "address_line2", "city", "state", "country", "pincode", "aadhaar_number",
  "blood_group", "date_of_birth", "phone", "centre_x_no", "cell", "email", "whatsapp_facebook", "family_surname", "gothram",
  "natchathiram", "occupation", "occupation_address", "native_place_address", "introducer_name", "introducer_phone",
  "introducer_reg_no", "declaration_place", "declaration_date",
] as const;

/** Today's date in the user's local time zone (not UTC), as YYYY-MM-DD. */
export const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

export function toFormValues(src: Partial<MemberFormData> & { declaration_accepted?: boolean; declaration_place?: string | null; declaration_date?: string | null }): FormValues {
  const v = {} as Record<string, string | boolean>;
  for (const f of TEXT_FIELDS) v[f] = ((src as Record<string, unknown>)[f] as string | null | undefined) ?? "";
  v.aadhaar_number = "";
  v.country = (v.country as string) || "India";
  v.show_contact_in_directory = src.show_contact_in_directory ?? true;
  v.show_address_in_directory = src.show_address_in_directory ?? true;
  v.declaration_accepted = src.declaration_accepted ?? false;
  v.declaration_date = (v.declaration_date as string) || today();
  return v as unknown as FormValues;
}

/**
 * Build the API payload. Empty strings become null. A blank Aadhaar field means
 * "keep the stored number" (it is never sent back to the browser in full).
 */
export function toPayload(values: FormValues, opts: { includeIntroducer?: boolean; includeDeclaration?: boolean } = {}) {
  const { includeIntroducer = true, includeDeclaration = true } = opts;
  const out: Record<string, unknown> = {};
  for (const f of TEXT_FIELDS) {
    if (!includeIntroducer && f.startsWith("introducer_")) continue;
    if (!includeDeclaration && f.startsWith("declaration_")) continue;
    const raw = (values[f] ?? "").toString().trim();
    out[f] = raw === "" ? null : raw;
  }
  if (!values.aadhaar_number.trim()) delete out.aadhaar_number;
  out.show_contact_in_directory = values.show_contact_in_directory;
  out.show_address_in_directory = values.show_address_in_directory;
  if (includeDeclaration) out.declaration_accepted = values.declaration_accepted;
  return out;
}

const req = (label: string) => z.string().trim().min(1, `${label} is required`);
const mandatory = (label: string) => z.string().trim().min(1, `${label} is mandatory`);
const phoneOpt = z.string().trim().refine((v) => v === "" || /^\+?[0-9]{7,15}$/.test(v.replace(/[\s\-()]/g, "")), "Enter a valid phone number");

/** Field-level rules shared by every form variant. */
const base = z.object({
  full_name: req("Name").max(150),
  father_name: req("Father's name").max(150),
  address_line1: req("Address").max(255),
  address_line2: z.string().max(255),
  city: req("City/Town/Village").max(120),
  state: req("State").max(120),
  country: req("Country").max(120),
  pincode: req("Pincode"),
  aadhaar_number: z.string().trim().refine((v) => v === "" || isValidAadhaar(v), "Enter a valid 12-digit Aadhaar number"),
  blood_group: z.string(),
  date_of_birth: req("Date of birth"),
  phone: phoneOpt,
  centre_x_no: z.string().max(30),
  cell: req("Cell (mobile number)").refine((v) => /^\+?[0-9]{7,15}$/.test(v.replace(/[\s\-()]/g, "")), "Enter a valid mobile number"),
  email: z.string().trim().refine((v) => v === "" || z.string().email().safeParse(v).success, "Enter a valid email address"),
  whatsapp_facebook: z.string().max(255),
  family_surname: z.string().max(120),
  gothram: z.string().max(120),
  natchathiram: z.string().max(120),
  occupation: z.string().max(150),
  occupation_address: z.string().max(1000),
  native_place_address: z.string().max(1000),
  introducer_name: z.string().max(150),
  introducer_phone: phoneOpt,
  introducer_reg_no: z.string().max(50),
  show_contact_in_directory: z.boolean(),
  show_address_in_directory: z.boolean(),
  declaration_accepted: z.boolean(),
  declaration_place: z.string().max(120),
  declaration_date: z.string(),
});

function common(minAge: number) {
  return (v: z.infer<typeof base>, ctx: z.RefinementCtx) => {
    if (v.pincode && !isValidPincode(v.pincode.trim(), v.country)) {
      ctx.addIssue({ code: "custom", path: ["pincode"], message: "Enter a valid pincode (6 digits for India)" });
    }
    if (v.date_of_birth) {
      const age = ageOn(v.date_of_birth);
      if (new Date(v.date_of_birth) > new Date()) ctx.addIssue({ code: "custom", path: ["date_of_birth"], message: "Date of birth cannot be in the future" });
      else if (age < minAge) ctx.addIssue({ code: "custom", path: ["date_of_birth"], message: `Applicant must have completed ${minAge} years` });
    }
  };
}

/** Rules for submitting an online application – the three introducer fields are mandatory. */
export const submissionSchema = (minAge = 18) => base.extend({
  introducer_name: mandatory("Introduced by Sri").max(150),
  introducer_phone: mandatory("Introducer phone no.").refine((v) => /^\+?[0-9]{7,15}$/.test(v.replace(/[\s\-()]/g, "")), "Enter a valid phone number"),
  introducer_reg_no: mandatory("Introducer registration no.").max(50),
  declaration_accepted: z.boolean().refine((v) => v, "Please confirm the declaration"),
  declaration_place: req("Place").max(120),
  declaration_date: req("Date"),
}).superRefine(common(minAge));

/** Draft saving checks formats only (no required fields). */
export const draftSchema = base.partial().extend({
  aadhaar_number: base.shape.aadhaar_number,
  phone: phoneOpt, cell: phoneOpt, introducer_phone: phoneOpt,
  show_contact_in_directory: z.boolean(), show_address_in_directory: z.boolean(), declaration_accepted: z.boolean(),
});

/** Admin / member profile editing: personal details required, introducer optional. */
export const profileSchema = (minAge = 18) => base.superRefine(common(minAge));

/** zodResolver typed for our form value shapes (schemas validate a superset of the edited fields). */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const formResolver = <T extends FieldValues>(schema: any): Resolver<T> => zodResolver(schema) as unknown as Resolver<T>;
