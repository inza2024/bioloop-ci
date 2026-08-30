"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, api } from "@/lib/api";
import type { AuthContext } from "@/lib/types";


export function PilotAccess({
  onContextChange,
}: {
  onContextChange: (context: AuthContext | null) => void;
}) {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [context, setContext] = useState<AuthContext | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    display_name: "",
    email: "",
    password: "",
    organization_name: "",
    organization_type: "producer",
  });

  useEffect(() => {
    api.me().then((result) => {
      setContext(result);
      onContextChange(result);
    }).catch((reason) => {
      if (!(reason instanceof ApiError) || reason.status !== 401) setError(reason.message);
    });
  }, [onContextChange]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = mode === "login"
        ? await api.login({ email: form.email, password: form.password })
        : await api.register(form);
      setContext(result);
      onContextChange(result);
      router.push(result.portal_path);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Erreur inattendue");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="pilot-access section-shell" id="pilot-access" aria-labelledby="pilot-access-title">
      <div className="section-heading">
        <div>
          <span className="section-index">PILOTE</span>
          <h2 id="pilot-access-title">Compte local et portail attribué</h2>
        </div>
        <p>Session serveur HttpOnly · protection CSRF · aucune identité stockée dans localStorage.</p>
      </div>
      {context ? (
        <article className="pilot-session-card" data-testid="pilot-session">
          <div>
            <span className="pilot-security-label">{context.pilot_security_label}</span>
            <h3>{context.user.display_name}</h3>
            <p>{context.active_membership.organization_name} · {context.active_membership.role}</p>
          </div>
          <div className="pilot-session-actions">
            <button className="primary-button" type="button" onClick={() => router.push(context.portal_path)}>
              Ouvrir mon portail
            </button>
            <button className="secondary-button" type="button" onClick={async () => {
              await api.logout();
              setContext(null);
              onContextChange(null);
            }}>Se déconnecter</button>
          </div>
        </article>
      ) : (
        <div className="pilot-auth-grid">
          <aside>
            <span>Fondation pilote</span>
            <h3>Une identité réelle pour le pilote local, sans prétention de sécurité certifiée.</h3>
            <ul>
              <li>Producteur et client : appartenance active après inscription.</li>
              <li>Logistique et unité : compte créé en attente de validation.</li>
              <li>Contrôle et coordination : invitation administrateur obligatoire.</li>
            </ul>
          </aside>
          <form onSubmit={submit} data-testid="pilot-auth-form">
            <div className="auth-tabs" role="tablist" aria-label="Accès pilote">
              <button type="button" className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Connexion</button>
              <button type="button" className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Créer un compte</button>
            </div>
            {mode === "register" && (
              <>
                <label>Nom complet<input data-testid="register-name" value={form.display_name} minLength={2} maxLength={100} onChange={(event) => setForm({ ...form, display_name: event.target.value })} required /></label>
                <label>Organisation<input data-testid="register-organization" value={form.organization_name} minLength={2} maxLength={120} onChange={(event) => setForm({ ...form, organization_name: event.target.value })} required /></label>
                <label>Type d’organisation<select data-testid="register-organization-type" value={form.organization_type} onChange={(event) => setForm({ ...form, organization_type: event.target.value })}>
                  <option value="producer">Producteur</option>
                  <option value="client">Client / agriculteur</option>
                  <option value="logistician">Logistique — validation requise</option>
                  <option value="processing_unit">Unité — validation requise</option>
                </select></label>
              </>
            )}
            <label>Email<input data-testid="auth-email" type="email" autoComplete="email" value={form.email} maxLength={254} onChange={(event) => setForm({ ...form, email: event.target.value })} required /></label>
            <label>Mot de passe<input data-testid="auth-password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={mode === "register" ? 12 : 1} maxLength={128} value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required /></label>
            {mode === "register" && <small>12 caractères minimum, avec majuscule, minuscule et chiffre.</small>}
            <button data-testid="pilot-auth-submit" className="primary-button full" disabled={busy} type="submit">{busy ? "Traitement…" : mode === "login" ? "Se connecter" : "Créer le compte local"}</button>
            {error && <p className="auth-error" role="alert">{error}</p>}
          </form>
        </div>
      )}
    </section>
  );
}
