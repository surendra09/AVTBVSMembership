import { Emblem } from "@/components/Brand";
import { usePublicConfig } from "@/hooks/usePublicConfig";

export function Footer({ compact = false }: { compact?: boolean }) {
  const { organisation: o } = usePublicConfig();
  return (
    <footer className="no-print border-t border-forest/20 bg-forest text-white/85">
      <div className={`mx-auto flex max-w-6xl flex-col gap-6 px-4 sm:px-6 ${compact ? "py-5" : "py-10"} md:flex-row md:items-start md:justify-between`}>
        <div className="flex items-start gap-4">
          <Emblem size={compact ? 40 : 56} />
          <div>
            <p className="font-display text-lg text-white">{o.full_name}</p>
            {!compact && <p className="font-display text-champagne" lang="te">{o.telugu_name}</p>}
            <p className="text-sm text-white/70">{o.registration}</p>
            {!compact && <p className="text-sm text-white/70">Formerly known as {o.formerly_known_as}</p>}
          </div>
        </div>
        <address className="not-italic text-sm leading-relaxed text-white/80">
          {o.address}<br />
          Phone <a href={`tel:${o.phone.replace(/[^0-9+]/g, "")}`} className="hover:text-white">{o.phone}</a><br />
          <a href={`mailto:${o.email}`} className="hover:text-white">{o.email}</a>
        </address>
      </div>
    </footer>
  );
}
