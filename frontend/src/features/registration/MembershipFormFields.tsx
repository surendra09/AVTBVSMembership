import type { ReactNode } from "react";
import type { FieldErrors, UseFormRegister } from "react-hook-form";
import { Checkbox, SelectField, TextAreaField, TextField } from "@/components/ui/Form";
import { today, type FormValues } from "./formModel";

interface Props {
  register: UseFormRegister<FormValues>;
  errors: FieldErrors<FormValues>;
  serverErrors?: Record<string, string>;
  bloodGroups: string[];
  showIntroducer?: boolean;
  introducerRequired?: boolean;
  aadhaarMasked?: string | null;
  disabled?: boolean;
  /** Fields that must not be changed in this context (e.g. introducer data for members). */
  lockIntroducer?: boolean;
}

/** One section of the official form, styled as a ruled block of the paper register. */
export function FormSection({ title, description, children }: { title: string; description?: ReactNode; children: ReactNode }) {
  return (
    <fieldset className="register">
      <legend className="sr-only">{title}</legend>
      <div className="register-section" aria-hidden="true">{title}</div>
      <div className="space-y-4 p-4 sm:p-5">
        {description && <p className="text-[15px] text-ink-soft">{description}</p>}
        {children}
      </div>
    </fieldset>
  );
}

export function MembershipFormFields({ register, errors, serverErrors = {}, bloodGroups, showIntroducer = true,
  introducerRequired = true, aadhaarMasked, disabled, lockIntroducer }: Props) {
  const err = (k: keyof FormValues) => errors[k]?.message?.toString() ?? serverErrors[k];
  const grid = "grid gap-4 sm:grid-cols-2";
  return (
    <div className="space-y-6">
      <FormSection title="Personal details">
        <div className={grid}>
          <TextField label="Name" required autoComplete="name" disabled={disabled} error={err("full_name")} {...register("full_name")} />
          <TextField label="Father's name" required disabled={disabled} error={err("father_name")} {...register("father_name")} />
        </div>
        <TextField label="Address" required autoComplete="address-line1" disabled={disabled} error={err("address_line1")} {...register("address_line1")} />
        <TextField label="Address (line 2)" autoComplete="address-line2" disabled={disabled} error={err("address_line2")} {...register("address_line2")} />
        <div className="grid gap-4 sm:grid-cols-3">
          <TextField label="City/Town/Village" required autoComplete="address-level2" disabled={disabled} error={err("city")} {...register("city")} />
          <TextField label="State" required autoComplete="address-level1" disabled={disabled} error={err("state")} {...register("state")} />
          <TextField label="Country" required autoComplete="country-name" disabled={disabled} error={err("country")} {...register("country")} />
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <TextField label="Pincode" required inputMode="numeric" autoComplete="postal-code" disabled={disabled} error={err("pincode")} {...register("pincode")} />
          <TextField label="Date of birth" required type="date" max={today()} disabled={disabled}
            error={err("date_of_birth")} {...register("date_of_birth")} />
          <SelectField label="Blood group" placeholder="Select" options={bloodGroups.map((b) => ({ value: b, label: b }))}
            disabled={disabled} error={err("blood_group")} {...register("blood_group")} />
        </div>
        <TextField label="Aadhaar card no." inputMode="numeric" autoComplete="off" disabled={disabled}
          placeholder={aadhaarMasked ? `${aadhaarMasked} (leave blank to keep)` : "12-digit number"}
          hint="Stored encrypted. Only the office can see the full number; it never appears in the directory."
          error={err("aadhaar_number")} {...register("aadhaar_number")} />
      </FormSection>

      <FormSection title="Contact details">
        <div className="grid gap-4 sm:grid-cols-3">
          <TextField label="Phone" type="tel" hint="Landline, if any" disabled={disabled} error={err("phone")} {...register("phone")} />
          <TextField label="Centre X No." disabled={disabled} error={err("centre_x_no")} {...register("centre_x_no")} />
          <TextField label="Cell" required type="tel" autoComplete="tel" hint="Mobile number" disabled={disabled} error={err("cell")} {...register("cell")} />
        </div>
        <div className={grid}>
          <TextField label="E-mail" type="email" autoComplete="email" disabled={disabled} error={err("email")} {...register("email")} />
          <TextField label="WhatsApp/Facebook" disabled={disabled} error={err("whatsapp_facebook")} {...register("whatsapp_facebook")} />
        </div>
      </FormSection>

      <FormSection title="Family details">
        <div className="grid gap-4 sm:grid-cols-3">
          <TextField label="Family surname" disabled={disabled} error={err("family_surname")} {...register("family_surname")} />
          <TextField label="Gothram" disabled={disabled} error={err("gothram")} {...register("gothram")} />
          <TextField label="Natchathiram" disabled={disabled} error={err("natchathiram")} {...register("natchathiram")} />
        </div>
      </FormSection>

      <FormSection title="Occupation and native place">
        <TextField label="Occupation" disabled={disabled} error={err("occupation")} {...register("occupation")} />
        <TextAreaField label="Occupation address" rows={2} disabled={disabled} error={err("occupation_address")} {...register("occupation_address")} />
        <TextAreaField label="Native place address" rows={2} disabled={disabled} error={err("native_place_address")} {...register("native_place_address")} />
      </FormSection>

      {showIntroducer && (
        <FormSection title="Introducer details"
          description={introducerRequired ? "An existing member must introduce you. All three details are mandatory. The registration number is your introducer's own membership number." : undefined}>
          <TextField label="Introduced by Sri" required={introducerRequired} disabled={disabled || lockIntroducer}
            error={err("introducer_name")} {...register("introducer_name")} />
          <div className={grid}>
            <TextField label="Introducer phone no." type="tel" required={introducerRequired} disabled={disabled || lockIntroducer}
              error={err("introducer_phone")} {...register("introducer_phone")} />
            <TextField label="Introducer reg. no." required={introducerRequired} disabled={disabled || lockIntroducer}
              hint="The introducer's membership number" error={err("introducer_reg_no")} {...register("introducer_reg_no")} />
          </div>
        </FormSection>
      )}

      <FormSection title="Member directory privacy" description="Approved members can see each other's details in the member directory. Choose what other members may see about you.">
        <Checkbox label="Show my phone, cell, email and WhatsApp to other members" disabled={disabled} {...register("show_contact_in_directory")} />
        <Checkbox label="Show my address and occupation address to other members" disabled={disabled} {...register("show_address_in_directory")} />
      </FormSection>
    </div>
  );
}
