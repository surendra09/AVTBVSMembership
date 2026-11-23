import { ButtonLink } from "@/components/ui/Button";
import { PageHeader, Panel } from "@/components/ui/Data";
import { useAuth } from "@/features/auth/AuthContext";
import { usePublicConfig } from "@/hooks/usePublicConfig";

export default function BeriChettyOverviewPage() {
  const { me } = useAuth();
  const { organisation: o, form, active_member_count } = usePublicConfig();

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-10 sm:px-6">
      <PageHeader
        title="Beri Chetty Overview"
        description={<>{o.full_name} — formerly {o.formerly_known_as}, {o.registration}.</>}
      />

      <Panel title="About the Sabha">
        <p className="font-display text-[clamp(1.4rem,1.1rem+1.5vw,2rem)] leading-[1.3] text-forest" lang="te">
          {o.telugu_name}
        </p>
        <p className="mt-2 text-[17px] text-ink">{o.full_name}</p>
        <p className="mt-1 text-ink-soft">Formerly known as {o.formerly_known_as}, {o.registration}.</p>
        <p className="mt-4 text-ink-soft">
          The Sabha maintains the official membership register of the {o.community_name}. This website brings that
          register online: members of the community can apply for life membership, follow their application as the
          Membership Enrollment Committee verifies it, and, once approved, receive an official membership number.
        </p>
        <p className="mt-3 text-ink-soft">
          Approved members are entered in both a public directory and a members-only directory, and are kept informed
          by website, email and SMS. Existing paper members are also recorded, so the register stays complete.
        </p>
        {active_member_count > 0 && (
          <p className="mt-4 border-l-2 border-champagne-600 pl-4 text-[15px] text-ink-soft">
            {active_member_count.toLocaleString("en-IN")} members are currently in the register.
          </p>
        )}
      </Panel>

      <Panel title="Community Heritage, History & Tradition">
        <p className="text-[13px] font-medium uppercase tracking-[0.2em] text-ink-muted">Welcome to the</p>
        <h3 className="mt-1 font-display text-[clamp(1.5rem,1.2rem+1.6vw,2.1rem)] leading-tight text-forest">
          Beri Chettiar Community
        </h3>
        <p className="mt-3 border-l-2 border-champagne-600 pl-4 font-display text-lg italic text-forest">
          "Our History. Our Heritage. Our Identity."
        </p>

        <div className="mt-5 space-y-4 text-ink-soft">
          <p>
            Welcome to a platform dedicated to the history, culture, traditions, and heritage of the Beri Chettiar
            community.
          </p>
          <p>
            Our community's story is part of the rich cultural history of Andhra Pradesh, Tamil Nadu and South India.
            Through generations, families have preserved their traditions, religious beliefs, family relationships, and
            community identity.
          </p>
          <p>
            Historical literature, including <span className="italic text-ink">Castes and Tribes of Southern India</span>,
            documents traditional accounts of Beri Chettiar origins, customs, merchant traditions, and community
            divisions. These records provide an important starting point for understanding our past, while family
            histories, temple records, inscriptions, and oral traditions can help us learn more.
          </p>
          <p>
            This Beri Chettiar Community aims to bring our community together, preserve ancestral knowledge, document
            family lineages, and share our heritage with younger generations.
          </p>
        </div>

        <blockquote className="mt-6 border-l-2 border-forest/30 pl-4 font-display text-[17px] italic text-forest">
          "Let us discover our roots, preserve our traditions, and pass our heritage on to future generations."
        </blockquote>
      </Panel>

      <Panel title="The community">
        <p className="text-ink-soft">
          The Sabha serves the <span className="text-ink">{o.community_name}</span>. The public register shows each
          member's name and father's name only; full contact and family details are visible to approved members after
          they log in.
        </p>
        <p className="mt-4 border-l-2 border-champagne-600 pl-4 text-[15px] text-ink-soft">
          Membership is open to those who have completed {form.minimum_age_years} years and belong to the{" "}
          {o.community_name}.
        </p>
      </Panel>

      <Panel title="Visit or contact the Sabha">
        <dl className="grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-[13px] font-medium uppercase tracking-wide text-ink-muted">Address</dt>
            <dd className="mt-1 text-ink-soft">{o.address}</dd>
          </div>
          <div>
            <dt className="text-[13px] font-medium uppercase tracking-wide text-ink-muted">Phone</dt>
            <dd className="mt-1 text-ink-soft"><a className="hover:text-forest" href={`tel:${o.phone}`}>{o.phone}</a></dd>
          </div>
          <div>
            <dt className="text-[13px] font-medium uppercase tracking-wide text-ink-muted">Email</dt>
            <dd className="mt-1 break-words text-ink-soft"><a className="hover:text-forest" href={`mailto:${o.email}`}>{o.email}</a></dd>
          </div>
          <div>
            <dt className="text-[13px] font-medium uppercase tracking-wide text-ink-muted">Registration</dt>
            <dd className="mt-1 text-ink-soft">{o.registration}</dd>
          </div>
        </dl>
      </Panel>

      {!me && (
        <div className="flex flex-wrap gap-3">
          <ButtonLink to="/register">Apply for membership</ButtonLink>
          <ButtonLink to="/directory" variant="secondary">Member directory</ButtonLink>
        </div>
      )}
    </div>
  );
}
