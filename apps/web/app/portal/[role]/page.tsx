"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ApiError, api } from "@/lib/api";
import type { AuthPortal, DemoRole } from "@/lib/types";


const roleLabels: Record<DemoRole, string> = {
  producer: "Producteur",
  logistician: "Logistique / collecte",
  processing_unit_operator: "Unité de transformation",
  field_controller: "Contrôle terrain",
  bioloop_coordinator: "Coordination BioLoop",
  client_farmer: "Client / agriculteur",
};

export default function AuthenticatedPortalPage() {
  const params = useParams<{ role: string }>();
  const router = useRouter();
  const [portal, setPortal] = useState<AuthPortal | null>(null);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.me()
      .then(async (context) => {
        if (context.portal_path !== `/portal/${params.role}`) {
          router.replace(context.portal_path);
          return null;
        }
        return api.authPortal(params.role);
      })
      .then((data) => {
        if (data) setPortal(data);
      })
      .catch((reason) => {
        if (reason instanceof ApiError && reason.status === 401) {
          router.replace("/#pilot-access");
          return;
        }
        setError(reason instanceof Error ? reason.message : "Erreur inattendue");
      });
  }, [params.role, router]);

  const filteredDeclarations = useMemo(() => {
    const query = filter.toLocaleLowerCase();
    return (portal?.declarations ?? []).filter((item) =>
      `${item.id} ${item.producer_name} ${item.waste_type_id}`.toLocaleLowerCase().includes(query),
    );
  }, [filter, portal]);

  if (error) return <main className="portal-page"><div className="error-banner">{error}</div></main>;
  if (!portal) return <main className="portal-page"><p>Chargement du portail attribué…</p></main>;
  const { context } = portal;
  const role = context.active_membership.role;

  return (
    <main className="portal-page" data-testid="authenticated-portal">
      <nav className="portal-mobile-nav" aria-label="Navigation du portail">
        <a className="brand" href="/"><span className="brand-mark">BL</span><span>BioLoop <em>CI</em></span></a>
        <a href="#overview">Aperçu</a>
        <a href="#objects">Objets</a>
        <a href="#proof">Preuves</a>
      </nav>
      <header className="portal-page-hero" id="overview">
        <div>
          <span className="pilot-security-label">{context.pilot_security_label}</span>
          <p>{context.user.display_name}</p>
          <h1>{roleLabels[role]}</h1>
          <strong>{context.active_membership.organization_name}</strong>
        </div>
        <span className={`membership-status ${context.active_membership.status}`}>
          {context.active_membership.status === "active" ? "Appartenance active" : "Validation en attente"}
        </span>
      </header>

      <section className="portal-page-grid">
        <article className="portal-overview-card">
          <span>Action principale</span>
          <h2>{portal.next_action}</h2>
          {role === "producer" && context.active_membership.status === "active" && (
            <a className="primary-button" href="/#declaration">Créer une déclaration P1</a>
          )}
        </article>
        <article className="portal-counter-card">
          <span>Compteurs du rôle</span>
          <div>{Object.entries(portal.counters).map(([key, value]) => <p key={key}><strong>{value}</strong>{key}</p>)}</div>
        </article>
        <article className="portal-proof-card" id="proof">
          <span>Niveaux de preuve</span>
          <h2>{portal.proof_summary}</h2>
          <p>Aucune donnée P1/P2/P3 n’est promue automatiquement en P4 ou P5.</p>
        </article>
      </section>

      <section className="portal-object-section" id="objects">
        <div className="portal-filter-row">
          <div><span>Objets autorisés</span><h2>Données de l’organisation active</h2></div>
          <label>Filtrer<input data-testid="portal-filter" value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="identifiant, producteur, type…" /></label>
        </div>
        {filteredDeclarations.length ? filteredDeclarations.map((item) => (
          <article className="portal-object-card" key={item.id}>
            <code>{item.id}</code><strong>{item.producer_name}</strong><span>{item.quantity_kg} kg · P1 déclaré</span>
          </article>
        )) : <p className="portal-empty">Aucun objet correspondant dans la portée de cette organisation.</p>}
      </section>

      <aside className="portal-memberships">
        <h2>Organisations et rôles accessibles</h2>
        {context.memberships.map((membership) => (
          <button
            key={membership.id}
            type="button"
            disabled={membership.id === context.active_membership.id}
            onClick={async () => {
              const updated = await api.activateMembership(membership.id);
              router.replace(updated.portal_path);
            }}
          >
            {membership.organization_name} · {roleLabels[membership.role]} · {membership.status}
          </button>
        ))}
        <button className="secondary-button" type="button" onClick={async () => {
          await api.logout();
          router.replace("/#pilot-access");
        }}>Se déconnecter</button>
      </aside>
    </main>
  );
}
