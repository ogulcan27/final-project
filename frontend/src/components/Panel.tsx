import type { ReactNode } from "react";

interface Props {
  title: ReactNode;
  right?: ReactNode;
  className?: string;
  children: ReactNode;
}

/** Bordered terminal panel with a compact title bar. */
export function Panel({ title, right, className = "", children }: Props) {
  return (
    <section className={`flex min-h-0 flex-col border border-line bg-panel ${className}`}>
      <header className="flex h-7 shrink-0 items-center justify-between border-b border-line px-2">
        <h2 className="text-[11px] font-semibold uppercase tracking-widest text-accent">{title}</h2>
        {right}
      </header>
      <div className="min-h-0 flex-1">{children}</div>
    </section>
  );
}
