import { useState, type ReactNode } from "react";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  className?: string;
}

export function Table<T>({ columns, rows, rowKey, onRowClick, caption }: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  onRowClick?: (row: T) => void;
  caption?: string;
}) {
  return (
    <div className="overflow-x-auto border border-line bg-white">
      <table className="w-full min-w-[640px] border-collapse text-left text-[15px]">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr className="border-b border-forest/20 bg-forest-50">
            {columns.map((c) => (
              <th key={c.key} scope="col" className={`px-4 py-2.5 text-sm font-semibold text-forest ${c.className ?? ""}`}>{c.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)}
              className={`border-b border-line last:border-b-0 ${onRowClick ? "cursor-pointer hover:bg-ivory" : ""}`}
              onClick={onRowClick ? () => onRowClick(row) : undefined}>
              {columns.map((c) => <td key={c.key} className={`px-4 py-3 align-middle ${c.className ?? ""}`}>{c.render(row)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Pagination({ page, pages, total, onPage, noun = "records" }: { page: number; pages: number; total: number; onPage: (p: number) => void; noun?: string }) {
  if (total === 0) return null;
  return (
    <nav className="mt-4 flex items-center justify-between gap-4 text-sm text-ink-soft" aria-label="Pagination">
      <span>{total.toLocaleString("en-IN")} {noun}</span>
      <div className="flex items-center gap-1">
        <button className="rounded p-1.5 hover:bg-sage disabled:opacity-40" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Previous page">
          <ChevronLeft className="h-5 w-5" />
        </button>
        <span className="px-2">Page {page} of {pages}</span>
        <button className="rounded p-1.5 hover:bg-sage disabled:opacity-40" disabled={page >= pages} onClick={() => onPage(page + 1)} aria-label="Next page">
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>
    </nav>
  );
}

export function SearchInput({ value, onChange, placeholder, label = "Search", className = "" }: { value: string; onChange: (v: string) => void; placeholder?: string; label?: string; className?: string }) {
  return (
    <label className={`relative block ${className}`}>
      <span className="sr-only">{label}</span>
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
      <input type="search" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
        className="field-input pl-9" />
    </label>
  );
}

export function Tabs<T extends string>({ value, onChange, options }: { value: T; onChange: (v: T) => void; options: { value: T; label: string; count?: number }[] }) {
  return (
    <div role="tablist" className="flex flex-wrap gap-x-1 border-b border-line">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button key={o.value} role="tab" aria-selected={active} onClick={() => onChange(o.value)}
            className={`-mb-px border-b-2 px-3 py-2 text-[15px] transition-colors ${active ? "border-forest font-medium text-forest" : "border-transparent text-ink-soft hover:text-ink"}`}>
            {o.label}
            {o.count !== undefined && <span className="ml-1.5 rounded-sm bg-sage px-1.5 text-[13px] text-ink-soft">{o.count}</span>}
          </button>
        );
      })}
    </div>
  );
}

export function Panel({ title, action, children, className = "" }: { title?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`border border-line bg-white ${className}`}>
      {title && (
        <header className="flex items-center justify-between gap-3 border-b border-line px-5 py-3">
          <h2 className="text-lg">{title}</h2>
          {action}
        </header>
      )}
      <div className="px-5 py-4">{children}</div>
    </section>
  );
}

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1>{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-ink-soft">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

/** Read-only register rows (label cell + value), mirroring the paper form. */
export function RegisterRows({ rows }: { rows: { label: string; value: ReactNode }[] }) {
  return (
    <>
      {rows.map((r) => (
        <div key={r.label} className="register-row">
          <div className="register-label">{r.label}</div>
          <div className="register-value break-words">{r.value === null || r.value === undefined || r.value === "" ? <span className="text-ink-muted">—</span> : r.value}</div>
        </div>
      ))}
    </>
  );
}

export function Avatar({ src, name, size = 40 }: { src?: string | null; name: string; size?: number }) {
  const [failed, setFailed] = useState(false);
  const letters = name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join("");
  if (src && !failed) {
    return <img src={src} alt="" width={size} height={size} onError={() => setFailed(true)}
      className="shrink-0 rounded-full border border-line object-cover" style={{ width: size, height: size }} />;
  }
  return (
    <span aria-hidden="true" className="inline-flex shrink-0 items-center justify-center rounded-full bg-sage font-display text-forest"
      style={{ width: size, height: size, fontSize: size * 0.38 }}>{letters}</span>
  );
}
