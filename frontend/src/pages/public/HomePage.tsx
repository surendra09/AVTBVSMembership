import { ButtonLink } from "@/components/ui/Button";
import { homePathFor, useAuth } from "@/features/auth/AuthContext";
import { PublicDirectoryList } from "@/features/members/PublicDirectoryList";
import { usePublicConfig } from "@/hooks/usePublicConfig";

const STEPS = [
  { title: "Create an account", body: "Register with your email address and mobile number, and confirm both with the codes we send." },
  { title: "Fill in the application", body: "Complete the Life Membership Application form online and upload your photographs, identity proof and signature." },
  { title: "Name your introducer", body: "An existing member must introduce you. Their name, phone number and registration number are required." },
  { title: "Verification by the committee", body: "The Membership Enrollment Committee checks your details. If anything needs correcting, you will be told exactly what." },
  { title: "Receive your membership number", body: "Once approved you are entered in the register and receive your official membership number by SMS and email." },
];

export default function HomePage() {
  const { me } = useAuth();
  const { organisation: o, active_member_count } = usePublicConfig();
  return (
    <>
      <section className="border-b border-line bg-white">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1fr_auto] md:items-center md:py-16">
          <div className="max-w-2xl">
            <p className="font-display text-[clamp(1.6rem,1.1rem+2.4vw,2.9rem)] leading-[1.25] text-forest" lang="te">{o.telugu_name}</p>
            <h1 className="mt-3 text-[clamp(1.35rem,1.1rem+1vw,1.9rem)] text-ink">{o.full_name}</h1>
            <p className="mt-1 text-ink-soft">Formerly known as {o.formerly_known_as}, {o.registration}</p>
            <p className="mt-6 max-w-xl text-[17px] text-ink-soft">
              The Sabha's membership register, now online. Apply for life membership, follow your application, and, once approved, find fellow members.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              {me ? (
                <ButtonLink to={homePathFor(me)}>Go to my dashboard</ButtonLink>
              ) : (
                <>
                  <ButtonLink to="/register">Apply for membership</ButtonLink>
                  <ButtonLink to="/login" variant="secondary">Log in</ButtonLink>
                </>
              )}
            </div>
          </div>
          <div className="mx-auto flex flex-col items-center md:mx-0">
            <div className="flex h-56 w-56 items-center justify-center rounded-full border-[6px] border-forest bg-ivory shadow-[0_0_0_10px_#E7ECE8] sm:h-72 sm:w-72">
              <img src="/brand/emblem-400.png" alt="The Sabha's tree emblem" className="w-[78%]" />
            </div>
            <p className="mt-5 font-display text-2xl tracking-[0.18em] text-forest">AVTBVS</p>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-12 px-4 py-12 sm:px-6 lg:grid-cols-[1.15fr_1fr]">
        <div>
          <h2>Find a member</h2>
          <p className="mb-5 mt-1 text-ink-soft">
            {active_member_count > 0 ? `${active_member_count.toLocaleString("en-IN")} members are in the register. ` : ""}
            The public register shows each member's name and father's name only. Approved members can log in to see full details.
          </p>
          <PublicDirectoryList pageSize={8} />
        </div>
        <div>
          <h2>How membership works</h2>
          <ol className="mt-5 space-y-5">
            {STEPS.map((s, i) => (
              <li key={s.title} className="grid grid-cols-[2.25rem_1fr] gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-full border border-forest/30 font-display text-forest">{i + 1}</span>
                <div>
                  <p className="font-medium text-ink">{s.title}</p>
                  <p className="text-[15px] text-ink-soft">{s.body}</p>
                </div>
              </li>
            ))}
          </ol>
          <p className="mt-6 border-l-2 border-champagne-600 pl-4 text-[15px] text-ink-soft">
            Membership is open to those who have completed 18 years and belong to the {o.community_name}.
          </p>
        </div>
      </section>
    </>
  );
}
