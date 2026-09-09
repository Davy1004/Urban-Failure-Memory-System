import { Moon, Sun, Waves } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { Badge, Button } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/format";

const NAV = [
  { to: "/watchlist", label: "Watchlist" },
  { to: "/index", label: "Ward index" },
  { to: "/emerging", label: "Emerging" },
  { to: "/allocation", label: "Allocation" },
];

function ThemeToggle() {
  const [dark, setDark] = useState(
    () =>
      document.documentElement.dataset.theme === "dark" ||
      (!document.documentElement.dataset.theme &&
        window.matchMedia?.("(prefers-color-scheme: dark)").matches),
  );

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  }, [dark]);

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setDark((d) => !d)}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
    >
      {dark ? <Sun size={16} aria-hidden /> : <Moon size={16} aria-hidden />}
    </Button>
  );
}

export function AppShell() {
  const { user, signOut } = useAuth();

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-[500] border-b border-[var(--border)] bg-[var(--surface-1)]">
        {/* Wraps rather than overflowing. At 390px the logo, four nav items and
            the account controls do not fit on one line, and a header that
            overflows makes the whole page scroll sideways. */}
        <div className="mx-auto flex max-w-[1180px] flex-wrap items-center gap-x-4 gap-y-1 px-5 py-2 sm:h-14 sm:flex-nowrap sm:py-0">
          <div className="flex items-center gap-2">
            <Waves size={18} aria-hidden style={{ color: "var(--series-1)" }} />
            <span className="text-[14px] font-semibold tracking-tight">UFMS</span>
            <Badge tone="muted" className="hidden sm:inline-flex">
              Bengaluru
            </Badge>
          </div>

          <nav
            aria-label="Screens"
            className="-mx-1 order-3 flex min-w-0 basis-full items-center gap-1 overflow-x-auto px-1 sm:order-none sm:basis-auto"
          >
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  cn(
                    "rounded-md px-2.5 py-1.5 text-[13px] font-medium whitespace-nowrap transition-colors",
                    isActive
                      ? "bg-[var(--series-1-soft)] text-[var(--series-1)]"
                      : "text-[var(--text-secondary)] hover:bg-[var(--surface-page)]",
                  )
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            {user ? (
              <>
                <span className="hidden text-[12px] text-[var(--text-secondary)] sm:inline">
                  {user.name}
                  <span className="ml-1.5 text-[var(--text-muted)]">({user.role})</span>
                </span>
                <Button variant="ghost" size="sm" onClick={signOut}>
                  Sign out
                </Button>
              </>
            ) : null}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1180px] px-5 py-6">
        <Outlet />
      </main>

      <footer className="mx-auto max-w-[1180px] px-5 pb-10 text-[11px] leading-relaxed text-[var(--text-muted)]">
        Decision support for preventive municipal maintenance. Every figure on
        these screens is measured on BBMP grievance data 2020–2025 and reconciled
        against the published analysis; none is a forecast.
      </footer>
    </div>
  );
}
