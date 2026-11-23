import { useCallback, useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/services/api";
import type { NotificationItem, Page } from "@/types";
import { formatDateTime } from "@/utils/format";

export function NotificationBell({ allHref, light = false }: { allHref: string; light?: boolean }) {
  const [open, setOpen] = useState(false);
  const [count, setCount] = useState(0);
  const [items, setItems] = useState<NotificationItem[] | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const refreshCount = useCallback(() => {
    api.get<{ count: number }>("/notifications/unread-count").then((r) => setCount(r.data.count)).catch(() => undefined);
  }, []);

  useEffect(() => {
    refreshCount();
    const t = setInterval(refreshCount, 60_000);
    return () => clearInterval(t);
  }, [refreshCount]);

  useEffect(() => {
    if (!open) return;
    api.get<Page<NotificationItem>>("/notifications", { params: { page_size: 6 } }).then((r) => setItems(r.data.items)).catch(() => setItems([]));
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", esc); };
  }, [open]);

  async function openItem(n: NotificationItem) {
    if (!n.is_read) {
      await api.patch(`/notifications/${n.id}/read`).catch(() => undefined);
      refreshCount();
    }
    setOpen(false);
    if (n.link) navigate(n.link);
  }

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-haspopup="true"
        aria-label={count ? `Notifications, ${count} unread` : "Notifications"}
        className={`relative rounded p-2 ${light ? "text-white hover:bg-white/10" : "text-forest hover:bg-forest-50"}`}>
        <Bell className="h-5 w-5" />
        {count > 0 && (
          <span className="absolute right-0.5 top-0.5 min-w-[18px] rounded-full bg-register px-1 text-center text-[11px] font-semibold leading-[18px] text-white">
            {count > 9 ? "9+" : count}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-40 mt-2 w-[min(22rem,calc(100vw-2rem))] border border-line bg-white shadow-soft">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <span className="font-display text-forest">Notifications</span>
            {count > 0 && (
              <button className="text-sm text-forest hover:underline" onClick={async () => {
                await api.post("/notifications/read-all"); refreshCount();
                setItems((xs) => xs?.map((x) => ({ ...x, is_read: true })) ?? xs);
              }}>Mark all as read</button>
            )}
          </div>
          <ul className="max-h-96 overflow-auto">
            {items === null && <li className="px-4 py-6 text-sm text-ink-muted">Loading…</li>}
            {items?.length === 0 && <li className="px-4 py-6 text-sm text-ink-muted">You have no notifications yet.</li>}
            {items?.map((n) => (
              <li key={n.id}>
                <button onClick={() => openItem(n)} className={`block w-full border-b border-line px-4 py-3 text-left hover:bg-ivory ${n.is_read ? "" : "bg-forest-50/60"}`}>
                  <span className="flex items-start gap-2">
                    {!n.is_read && <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-register" aria-label="Unread" />}
                    <span className="min-w-0">
                      <span className="block text-[15px] font-medium text-ink">{n.title}</span>
                      <span className="line-clamp-2 block text-sm text-ink-soft">{n.message}</span>
                      <span className="mt-0.5 block text-[12px] text-ink-muted">{formatDateTime(n.created_at)}</span>
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <Link to={allHref} onClick={() => setOpen(false)} className="block px-4 py-2.5 text-center text-sm text-forest hover:bg-forest-50">
            See all notifications
          </Link>
        </div>
      )}
    </div>
  );
}
