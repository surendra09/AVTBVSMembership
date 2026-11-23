import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { Button, ButtonLink } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/Data";
import { Alert } from "@/components/ui/Feedback";
import { TextField } from "@/components/ui/Form";
import { OfficeUseFields, officePayload, type OfficeValues } from "@/features/admin/OfficeUseFields";
import { FormSection, MembershipFormFields } from "@/features/registration/MembershipFormFields";
import { profileSchema, toFormValues, toPayload, type FormValues, formResolver } from "@/features/registration/formModel";
import { usePublicConfig } from "@/hooks/usePublicConfig";
import { api, parseApiError } from "@/services/api";
import type { AdminMember } from "@/types";

type Values = FormValues & OfficeValues & { membership_number: string; enrolled_on: string };

export default function AddMemberPage() {
  const config = usePublicConfig();
  const navigate = useNavigate();
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [numberCheck, setNumberCheck] = useState<string | null>(null);

  const schema = profileSchema(config.form.minimum_age_years).and(z.object({
    membership_number: z.string().trim().min(1, "Enter the existing membership number").max(50),
    enrolled_on: z.string(),
  }).passthrough());
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Values>({
    defaultValues: { ...toFormValues({}), declaration_date: "", membership_number: "", enrolled_on: "" } as Values,
    resolver: formResolver(schema),
  });

  async function checkNumber(n: string) {
    setNumberCheck(null);
    if (!n.trim()) return;
    const { data } = await api.get<{ exists: boolean; member_name: string | null }>("/admin/members/check-number", { params: { number: n.trim() } });
    if (data.exists) setNumberCheck(`Already used by ${data.member_name}`);
  }

  const onSubmit = handleSubmit(async (v) => {
    setError(null);
    setServerErrors({});
    const body = {
      ...toPayload(v, { includeDeclaration: false }), ...officePayload(v as unknown as Record<string, unknown>),
      membership_number: v.membership_number.trim(), enrolled_on: v.enrolled_on || null,
      declaration_place: v.declaration_place || null, declaration_date: v.declaration_date || null,
    };
    try {
      const { data } = await api.post<AdminMember>("/admin/members", body);
      navigate(`/admin/members/${data.member_id}?created=1`);
    } catch (e) {
      const info = parseApiError(e, "Could not add the member.");
      setServerErrors(info.fieldErrors);
      setError(info.message);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  });

  return (
    <>
      <PageHeader title="Add an existing member" description="For members already registered on paper. They are added directly as active members with their existing number; no application or login account is needed." />
      {error && <div className="mb-5"><Alert tone="error">{error}</Alert></div>}
      <form onSubmit={onSubmit} noValidate className="space-y-6">
        <FormSection title="Registered membership">
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField label="Regd. Mem. No." required hint="Exactly as written in the register"
              error={errors.membership_number?.message ?? serverErrors.membership_number ?? numberCheck ?? undefined}
              {...register("membership_number", { onBlur: (e) => checkNumber(e.target.value) })} />
            <TextField label="Enrolment date" type="date" hint="If known" {...register("enrolled_on")} />
          </div>
        </FormSection>
        <MembershipFormFields register={register as never} errors={errors} serverErrors={serverErrors} bloodGroups={config.form.blood_groups} introducerRequired={false} />
        <FormSection title="Declaration on the paper form">
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField label="Place" {...register("declaration_place")} />
            <TextField label="Date" type="date" {...register("declaration_date")} />
          </div>
        </FormSection>
        <OfficeUseFields register={register} />
        <p className="text-[15px] text-ink-soft">Photographs and documents can be uploaded on the next screen.</p>
        <div className="flex justify-end gap-2">
          <ButtonLink variant="quiet" to="/admin/members">Cancel</ButtonLink>
          <Button type="submit" loading={isSubmitting}>Add member</Button>
        </div>
      </form>
    </>
  );
}
