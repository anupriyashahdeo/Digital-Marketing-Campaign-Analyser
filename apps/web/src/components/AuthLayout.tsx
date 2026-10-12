import type { ReactNode } from "react";

export default function AuthLayout({ title, subtitle, children }:
  { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="brand">Ad Campaign Analyser</div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
        {children}
      </section>
    </main>
  );
}
