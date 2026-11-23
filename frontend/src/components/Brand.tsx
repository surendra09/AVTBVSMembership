import { Link } from "react-router-dom";

/**
 * Official branding: the tree emblem extracted from the Sabha's annual report cover,
 * shown in a circular seal (as on the cover) beside the AVTBVS abbreviation.
 */
export function Emblem({ size = 44, className = "" }: { size?: number; className?: string }) {
  return (
    <span className={`inline-flex shrink-0 items-center justify-center rounded-full border border-champagne-600/60 bg-ivory ${className}`}
      style={{ width: size, height: size }}>
      <img src="/brand/emblem-192.png" alt="" className="h-[80%] w-[80%] object-contain" />
    </span>
  );
}

export function BrandMark({ to = "/", light = false, compact = false }: { to?: string; light?: boolean; compact?: boolean }) {
  return (
    <Link to={to} className="flex min-w-0 items-center gap-2.5" aria-label="AVTBVS Membership home">
      <Emblem size={compact ? 34 : 46} />
      <span className="min-w-0 leading-tight">
        <span className={`block whitespace-nowrap font-display ${compact ? "text-lg" : "text-xl"} tracking-wide ${light ? "text-white" : "text-forest"}`}>AVTBVS Membership</span>
        {!compact && (
          <span className={`block truncate text-[13px] ${light ? "text-champagne" : "text-ink-muted"}`}>Ayira Vaisyar Telugu Beri Vysya Sabha</span>
        )}
      </span>
    </Link>
  );
}
