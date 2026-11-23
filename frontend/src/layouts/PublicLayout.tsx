import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { BrandMark } from "@/components/Brand";
import { ButtonLink } from "@/components/ui/Button";
import { homePathFor, useAuth } from "@/features/auth/AuthContext";
import { Footer } from "./Footer";

export function PublicHeader() {
  const { me } = useAuth();
  const [open, setOpen] = useState(false);
  const link = ({ isActive }: { isActive: boolean }) =>
    `px-1 py-2 text-[15px] ${isActive ? "text-forest underline decoration-champagne-600 decoration-2 underline-offset-8" : "text-ink-soft hover:text-forest"}`;
  return (
    <header className="border-b border-line bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <BrandMark />
        <nav className="hidden items-center gap-6 md:flex" aria-label="Main">
          <NavLink to="/" end className={link}>Home</NavLink>
          <NavLink to="/beri-chetty-overview" className={link}>Beri Chetty</NavLink>
          <NavLink to="/directory" className={link}>Member directory</NavLink>
          {me ? (
            <ButtonLink to={homePathFor(me)} size="sm">My dashboard</ButtonLink>
          ) : (
            <>
              <NavLink to="/login" className={link}>Log in</NavLink>
              <ButtonLink to="/register" size="sm">Create account</ButtonLink>
            </>
          )}
        </nav>
        <button className="rounded p-2 text-forest md:hidden" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-label="Menu">
          {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>
      {open && (
        <nav className="border-t border-line px-4 pb-4 md:hidden" aria-label="Main mobile" onClick={() => setOpen(false)}>
          <NavLink to="/" end className="block py-2.5">Home</NavLink>
          <NavLink to="/beri-chetty-overview" className="block py-2.5">Beri Chetty</NavLink>
          <NavLink to="/directory" className="block py-2.5">Member directory</NavLink>
          {me ? <NavLink to={homePathFor(me)} className="block py-2.5 font-medium text-forest">My dashboard</NavLink> : (
            <>
              <NavLink to="/login" className="block py-2.5">Log in</NavLink>
              <NavLink to="/register" className="block py-2.5 font-medium text-forest">Create account</NavLink>
            </>
          )}
        </nav>
      )}
    </header>
  );
}

export function PublicLayout() {
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:bg-white focus:px-3 focus:py-2">Skip to content</a>
      <PublicHeader />
      <main id="main" className="flex-1"><Outlet /></main>
      <Footer />
    </div>
  );
}
