/**
 * The UI primitives, in the shadcn idiom: plain components over Tailwind
 * classes with `cva` variants, owned by this repo rather than imported from a
 * package.
 *
 * Everything is written against the palette tokens in `index.css`, never a raw
 * hex, so light and dark are one definition and the charts and the chrome
 * cannot drift apart.
 */
import { cva, type VariantProps } from "class-variance-authority";
import { AlertTriangle, Ban, Info, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/format";

// ---------------------------------------------------------------------------

export function Card({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-lg border border-[var(--border)] bg-[var(--surface-1)]",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  description,
  actions,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-start justify-between gap-3 px-5 pt-5 pb-3",
        className,
      )}
    >
      <div className="min-w-0">
        <h2 className="text-[15px] leading-tight font-semibold text-[var(--text-primary)]">
          {title}
        </h2>
        {description ? (
          <p className="mt-1 max-w-prose text-[13px] leading-relaxed text-[var(--text-secondary)]">
            {description}
          </p>
        ) : null}
      </div>
      {/* Not `shrink-0`: on a narrow screen a header action wide enough to
          exceed the viewport makes the whole page scroll sideways, and the
          badges in it wrap perfectly well on their own. */}
      {actions ? <div className="min-w-0 max-w-full">{actions}</div> : null}
    </div>
  );
}

export function CardBody({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return <div className={cn("px-5 pb-5", className)}>{children}</div>;
}

// ---------------------------------------------------------------------------

const buttonStyles = cva(
  "inline-flex items-center justify-center gap-2 rounded-md text-[13px] font-medium transition-colors " +
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--series-1)] " +
    "disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary:
          "bg-[var(--series-1)] text-white hover:brightness-110 active:brightness-95",
        outline:
          "border border-[var(--border-strong)] text-[var(--text-primary)] hover:bg-[var(--surface-page)]",
        ghost: "text-[var(--text-secondary)] hover:bg-[var(--surface-page)]",
      },
      size: {
        // 36px tall clears the 24px minimum hit target with room to spare.
        md: "h-9 px-3.5",
        sm: "h-8 px-2.5 text-[12px]",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "outline", size: "md" },
  },
);

export function Button({
  className,
  variant,
  size,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonStyles>) {
  return (
    <button className={cn(buttonStyles({ variant, size }), className)} {...props} />
  );
}

// ---------------------------------------------------------------------------

export function Input({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-9 w-full rounded-md border border-[var(--border-strong)] bg-[var(--surface-1)] px-3 text-[13px]",
        "text-[var(--text-primary)] placeholder:text-[var(--text-muted)]",
        "focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[var(--series-1)]",
        className,
      )}
      {...props}
    />
  );
}

export function Label({
  className,
  ...props
}: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn(
        "block text-[12px] font-medium text-[var(--text-secondary)]",
        className,
      )}
      {...props}
    />
  );
}

// ---------------------------------------------------------------------------

const badgeStyles = cva(
  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium whitespace-nowrap",
  {
    variants: {
      tone: {
        neutral:
          "border border-[var(--border-strong)] text-[var(--text-secondary)]",
        accent: "bg-[var(--series-1-soft)] text-[var(--series-1)]",
        muted: "text-[var(--text-muted)]",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export function Badge({
  className,
  tone,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeStyles>) {
  return <span className={cn(badgeStyles({ tone }), className)} {...props} />;
}

// ---------------------------------------------------------------------------

/**
 * A callout. Status colour never travels alone — every tone ships an icon and
 * a visible label, because two of the four status steps sit below 3:1 on the
 * light surface by design.
 */
const TONES: Record<
  "info" | "warning" | "critical",
  { color: string; icon: LucideIcon; label: string }
> = {
  info: { color: "var(--series-1)", icon: Info, label: "Note" },
  warning: { color: "var(--status-warning)", icon: AlertTriangle, label: "Caution" },
  critical: { color: "var(--status-critical)", icon: Ban, label: "Retracted" },
};

export function Callout({
  tone = "info",
  title,
  children,
  className,
}: {
  tone?: keyof typeof TONES;
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  const { color, icon: Icon, label } = TONES[tone];
  return (
    <div
      role="note"
      className={cn(
        "flex gap-3 rounded-md border border-[var(--border)] bg-[var(--surface-page)] p-3.5",
        className,
      )}
      style={{ borderLeft: `3px solid ${color}` }}
    >
      <Icon aria-hidden size={16} className="mt-0.5 shrink-0" style={{ color }} />
      <div className="min-w-0 text-[13px] leading-relaxed text-[var(--text-secondary)]">
        <span className="font-semibold text-[var(--text-primary)]">
          {title ?? label}
        </span>
        {": "}
        {children}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[13px]">{children}</table>
    </div>
  );
}

export function Th({
  className,
  numeric,
  children,
  ...props
}: React.ThHTMLAttributes<HTMLTableCellElement> & { numeric?: boolean }) {
  return (
    <th
      scope="col"
      className={cn(
        "border-b border-[var(--border)] px-3 py-2 text-[11px] font-medium tracking-wide text-[var(--text-muted)] uppercase",
        numeric ? "text-right" : "text-left",
        className,
      )}
      {...props}
    >
      {children}
    </th>
  );
}

export function Td({
  className,
  numeric,
  children,
  ...props
}: React.TdHTMLAttributes<HTMLTableCellElement> & { numeric?: boolean }) {
  return (
    <td
      className={cn(
        "border-b border-[var(--border)] px-3 py-2 text-[var(--text-primary)]",
        // Columns of numbers align; standalone values elsewhere do not.
        numeric ? "text-right tabular-nums" : "text-left",
        className,
      )}
      {...props}
    >
      {children}
    </td>
  );
}

// ---------------------------------------------------------------------------

/** Held at reduced opacity on refetch rather than flashed to a skeleton. */
export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div
      role="status"
      className="py-12 text-center text-[13px] text-[var(--text-muted)]"
    >
      {label}…
    </div>
  );
}

/**
 * The empty state. It says what is missing and how to produce it — it never
 * substitutes a plausible number, because an invented figure on a screen whose
 * whole point is measurement is worse than a blank one.
 */
export function Empty({ title, hint }: { title: string; hint?: ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-[var(--border-strong)] p-8 text-center">
      <p className="text-[13px] font-medium text-[var(--text-primary)]">{title}</p>
      {hint ? (
        <p className="mx-auto mt-1.5 max-w-md text-[12px] leading-relaxed text-[var(--text-secondary)]">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export function ErrorState({ error }: { error: Error }) {
  return (
    <Callout tone="critical" title="Could not load this screen">
      {error.message}
    </Callout>
  );
}
