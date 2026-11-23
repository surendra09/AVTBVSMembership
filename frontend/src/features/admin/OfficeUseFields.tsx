import type { UseFormRegister } from "react-hook-form";
import { TextAreaField, TextField } from "@/components/ui/Form";
import { FormSection } from "@/features/registration/MembershipFormFields";

export interface OfficeValues {
  verified_by: string;
  receipt_number: string;
  receipt_date: string;
  committee_chairman: string;
  committee_secretary: string;
  committee_president: string;
  office_notes: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function OfficeUseFields({ register }: { register: UseFormRegister<any> }) {
  return (
    <FormSection title="For office use only" description="Only administrators can see or change this section.">
      <div className="grid gap-4 sm:grid-cols-3">
        <TextField label="Verified by" {...register("verified_by")} />
        <TextField label="Rec. No." {...register("receipt_number")} />
        <TextField label="Receipt date" type="date" {...register("receipt_date")} />
      </div>
      <p className="text-sm font-medium text-forest">Membership Enrollment Committee, for AVTBV Sabha</p>
      <div className="grid gap-4 sm:grid-cols-3">
        <TextField label="Chairman" {...register("committee_chairman")} />
        <TextField label="Secretary" {...register("committee_secretary")} />
        <TextField label="President" {...register("committee_president")} />
      </div>
      <TextAreaField label="Office notes" rows={2} {...register("office_notes")} />
    </FormSection>
  );
}

export const OFFICE_KEYS = ["verified_by", "receipt_number", "receipt_date", "committee_chairman", "committee_secretary",
  "committee_president", "office_notes"] as const;

export function officePayload(v: Record<string, unknown>) {
  return Object.fromEntries(OFFICE_KEYS.map((k) => [k, (v[k] as string)?.toString().trim() || null]));
}
