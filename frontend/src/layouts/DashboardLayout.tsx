import { useEffect, useState, type ComponentType } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { LogOut, Menu, X } from "lucide-react";
import { BrandMark } from "@/components/Brand";
import { useAuth } from "@/features/auth/AuthContext";
import { NotificationBell } from "@/features/notifications/NotificationBell";
import { Footer } from "./Footer";

export interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  end?: boolean;
}
export interface NavGroup {
  title?: string;
  items: NavItem[];
}

const ROLE_LABEL = { USER: "Member account", ADMIN: "Administrator", SUPER_ADMIN: "Super Admin" } as const;

export function DashboardLayout({ groups, notificationsHref, homeHref }: { groups: NavGroup[]; notificationsHref: string; homeHref: string }) {
  const { me, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  useEffect(() => setOpen(false), [location.pathname]);

  async function doLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  const nav = (
    <nav aria-label="Dashboard" className="flex flex-1 flex-col gap-5 overflow-y-auto px-3 py-5">
      {groups.map((g, i) => (
        <div key={g.title ?? i}>
          {g.title && <p className="mb-1.5 px-3 text-[13px] text-champagne/90">{g.title}</p>}
          <ul className="space-y-0.5">
            {g.items.map((item) => (
              <li key={item.to}>
                <NavLink to={item.to} end={item.end}
                  className={({ isActive }) => `flex items-center gap-3 rounded px-3 py-2 text-[15px] transition-colors ${isActive
                    ? "bg-white/12 text-white shadow-[inset_3px_0_0_#D8C9A5]" : "text-white/75 hover:bg-white/5 hover:text-white"}`}>
                  <item.icon className="h-[18px] w-[18px] shrink-0" />
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
      <button onClick={doLogout} className="mt-auto flex items-center gap-3 rounded px-3 py-2 text-[15px] text-white/75 hover:bg-white/5 hover:text-white">
        <LogOut className="h-[18px] w-[18px]" /> Log out
      </button>
    </nav>
  );

  return (
    <div className="flex min-h-screen bg-ivory">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:bg-white focus:px-3 focus:py-2">Skip to content</a>
      {/* Desktop sidebar */}
      <aside className="no-print sticky top-0 hidden h-screen w-64 shrink-0 flex-col bg-forest lg:flex">
        <div className="border-b border-white/10 px-5 py-4"><BrandMark to={homeHref} light compact /></div>
        {nav}
      </aside>
      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-ink/40" onClick={() => setOpen(false)} />
          <aside className="relative flex h-full w-72 max-w-[85vw] flex-col bg-forest">
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-4">
              <BrandMark to={homeHref} light compact />
              <button onClick={() => setOpen(false)} aria-label="Close menu" className="rounded p-1 text-white"><X className="h-5 w-5" /></button>
            </div>
            {nav}
          </aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="no-print sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-line bg-white/95 px-4 py-2.5 backdrop-blur sm:px-6">
          <button className="rounded p-2 text-forest lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
            <Menu className="h-6 w-6" />
          </button>
          <span className="hidden font-display text-lg text-forest lg:block">AVTBVS Membership</span>
          <div className="flex items-center gap-2">
            <NotificationBell allHref={notificationsHref} />
            <div className="hidden text-right leading-tight sm:block">
              <p className="text-[15px] font-medium text-ink">{me?.user.full_name}</p>
              <p className="text-[13px] text-ink-muted">
                {me?.membership.membership_number && me.user.role === "USER" ? `Member no. ${me.membership.membership_number}` : ROLE_LABEL[me?.user.role ?? "USER"]}
              </p>
            </div>
          </div>
        </header>
        <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 sm:py-8"><Outlet /></main>
        <Footer compact />
      </div>
    </div>
  );
}
