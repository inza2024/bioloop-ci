"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type {
  AuditEvent,
  DemoActor,
  DemoRole,
  DemoWorkspace,
} from "@/lib/types";


const roleLabels: Record<DemoRole, string> = {
  producer: "Producteur",
  logistician: "Logistique / collecte",
  processing_unit_operator: "Unité de transformation",
  field_controller: "Contrôle terrain",
  bioloop_coordinator: "Coordination BioLoop",
  client_farmer: "Client / agriculteur",
};

const formatNumber = (value: string | number) =>
  new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 }).format(Number(value));

function Proof({ level, children }: { level: string; children: React.ReactNode }) {
  return <span className={`evidence evidence-${level.toLowerCase()}`}><strong>{level}</strong> {children}</span>;
}

interface MultiActorPortalsProps {
  onActorChange: (actor: DemoActor | null) => void;
}

export function MultiActorPortals({ onActorChange }: MultiActorPortalsProps) {
  const [actors, setActors] = useState<DemoActor[]>([]);
  const [selectedUserId, setSelectedUserId] = useState("USER-PROD-001");
  const [workspace, setWorkspace] = useState<DemoWorkspace | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [logisticsFile, setLogisticsFile] = useState<File | null>(null);
  const [producerFile, setProducerFile] = useState<File | null>(null);
  const [producerEvidenceMessage, setProducerEvidenceMessage] = useState("");
  const [measuredQuantity, setMeasuredQuantity] = useState("1200");
  const [decision, setDecision] = useState<"accepted" | "refused">("accepted");
  const [decisionReason, setDecisionReason] = useState("");
  const [verificationNote, setVerificationNote] = useState(
    "Contrôle terrain explicite réalisé dans le démonstrateur.",
  );
  const [auditFilters, setAuditFilters] = useState({
    actor_user_id: "",
    organization_id: "",
    object_type: "",
    correlation_id: "",
  });
  const [filteredAudit, setFilteredAudit] = useState<AuditEvent[] | null>(null);

  const refresh = useCallback(async (userId: string) => {
    const data = await api.demoWorkspace(userId);
    setWorkspace(data);
    onActorChange(data.actor);
  }, [onActorChange]);

  useEffect(() => {
    api.demoActors()
      .then((catalog) => {
        setActors(catalog.actors);
        return refresh(selectedUserId);
      })
      .catch((reason: Error) => setError(reason.message));
  }, [refresh, selectedUserId]);

  const changeActor = async (userId: string) => {
    setSelectedUserId(userId);
    setFilteredAudit(null);
    setError("");
  };

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    try {
      await action();
      await refresh(selectedUserId);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Erreur inattendue");
    } finally {
      setBusy(false);
    }
  };

  const confirmCollectionAndCreateLot = async (collectionId: string) => {
    const item = workspace?.logistics_collections.find(
      (entry) => entry.collection.id === collectionId,
    );
    if (!item || !logisticsFile) {
      setError("Joignez d’abord un PDF ou une image de pesée.");
      return;
    }
    await run(async () => {
      const evidence = await api.createEvidence(
        item.collection.declaration_id,
        logisticsFile,
        {
          category: "bon_pesee",
          captured_at: new Date().toISOString(),
          note: "Pièce logistique jointe en mode démonstration.",
        },
        selectedUserId,
      );
      const measurement = await api.createMeasurement(
        item.collection.declaration_id,
        {
          quantity_kg: measuredQuantity,
          unit: "kg",
          method: "balance_mobile",
          measured_at: new Date().toISOString(),
          device_reference: "BAL-DEMO-PORTAL",
          evidence_id: evidence.id,
          supersedes_measurement_id: null,
          note: "Pesée P3 saisie par la logistique de démonstration.",
        },
        selectedUserId,
      );
      await api.confirmCollection(
        collectionId,
        evidence.id,
        measurement.id,
        selectedUserId,
      );
      await api.createLot(
        item.collection.declaration_id,
        {
          measurement_id: measurement.id,
          processing_unit_id: item.collection.processing_unit_id,
          evidence_ids: [evidence.id],
        },
        selectedUserId,
      );
      setLogisticsFile(null);
    });
  };

  const uploadProducerEvidence = async (declarationId: string) => {
    if (!producerFile) {
      setError("Choisissez d’abord un PDF ou une image à documenter.");
      return;
    }
    setProducerEvidenceMessage("");
    await run(async () => {
      const evidence = await api.createEvidence(
        declarationId,
        producerFile,
        {
          category: "photo_gisement",
          captured_at: new Date().toISOString(),
          note: "Pièce P2 jointe par le producteur en mode démonstration.",
        },
        selectedUserId,
      );
      setProducerEvidenceMessage(`${evidence.id} enregistré en P2 sans vérification automatique.`);
      setProducerFile(null);
    });
  };

  const decideLot = (lotId: string) => run(() => api.decideLot(
    lotId,
    {
      decision,
      reason: decision === "refused" ? decisionReason : "",
      note: "Décision attribuée à l’opérateur de l’unité en mode démonstration.",
    },
    selectedUserId,
  ));

  const verifyLot = (lotId: string) => run(() => api.createVerification(
    {
      subject_type: "waste_lot",
      subject_id: lotId,
      outcome: "verified",
      note: verificationNote,
      idempotency_key: `portal:${lotId}:verified:v1`,
    },
    selectedUserId,
  ));

  const filterAudit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const filters = Object.fromEntries(
        Object.entries(auditFilters).filter(([, value]) => value.trim()),
      );
      setFilteredAudit(await api.audit(selectedUserId, filters));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Erreur inattendue");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="portal-section" id="portails" aria-labelledby="portal-title">
      <div className="section-shell">
        <div className="section-heading light">
          <div>
            <span className="section-index">05</span>
            <h2 id="portal-title">Collaborer par responsabilité</h2>
          </div>
          <p>Six espaces séparés, une identité attribuée à chaque événement, aucune authentification de production.</p>
        </div>

        <div className="demo-identity-bar">
          <div>
            <span className="demo-mode">Mode démonstration</span>
            <strong>{workspace?.actor.display_name ?? "Chargement des identités…"}</strong>
            <small>{workspace?.actor.organization_name}</small>
          </div>
          <label>
            Rôle et organisation actifs
            <select
              data-testid="demo-role-selector"
              value={selectedUserId}
              onChange={(event) => changeActor(event.target.value)}
            >
              {actors.map((actor) => (
                <option value={actor.user_id} key={actor.user_id}>
                  {roleLabels[actor.role]} — {actor.organization_name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="demo-auth-warning">Identité fictive sélectionnée dans le navigateur. Les autorisations sont contrôlées par l’API, mais ce mécanisme ne remplace ni connexion, ni MFA, ni gestion de session.</p>

        {error && <div className="error-banner portal-error" role="alert">{error}</div>}
        {workspace && (
          <div className="portal-shell" data-testid={`portal-${workspace.actor.role}`}>
            <header className="portal-header">
              <div>
                <span>{roleLabels[workspace.actor.role]}</span>
                <h3>{workspace.actor.organization_name}</h3>
              </div>
              <div className="permission-summary">
                {workspace.permissions.map((permission) => <code key={permission}>{permission}</code>)}
              </div>
            </header>

            {workspace.actor.role === "producer" && (
              <div className="portal-grid">
                <article className="portal-card portal-intro">
                  <Proof level="P1">Déclaration propre au site</Proof>
                  <h4>Déclarer pour {workspace.actor.site_id}</h4>
                  <p>Le formulaire 02 utilise désormais cette identité. L’API refusera tout autre site producteur.</p>
                  <a className="secondary-button" href="#declaration">Ouvrir le formulaire producteur</a>
                </article>
                {workspace.producer_declarations.map((item) => (
                  <article className="portal-card" key={item.declaration.id}>
                    <small>{item.declaration.id}</small>
                    <h4>{item.declaration.producer_name}</h4>
                    <p>{formatNumber(item.declaration.quantity_kg)} kg · {item.declaration.frequency}</p>
                    <dl className="portal-facts">
                      <div><dt>Unité proposée</dt><dd>{item.proposed_unit_id ?? "À sélectionner"}</dd></div>
                      <div><dt>Collecte</dt><dd>{item.collection_status ?? "Non assignée"}</dd></div>
                      <div><dt>Lot</dt><dd>{item.lot_status ?? "Non créé"}</dd></div>
                    </dl>
                    <strong className="next-action">{item.next_action}</strong>
                    <div className="portal-action-form compact">
                      <label>Documenter le gisement en P2<input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(event) => setProducerFile(event.target.files?.[0] ?? null)} /></label>
                      <button className="secondary-button" type="button" disabled={busy} onClick={() => uploadProducerEvidence(item.declaration.id)}>Joindre la preuve au gisement</button>
                      {producerEvidenceMessage && <small>{producerEvidenceMessage}</small>}
                    </div>
                  </article>
                ))}
              </div>
            )}

            {workspace.actor.role === "logistician" && (
              <div className="portal-grid">
                {workspace.logistics_collections.length === 0 && <p className="portal-empty">Aucune collecte assignée.</p>}
                {workspace.logistics_collections.map((item) => (
                  <article className="portal-card logistics-card" data-declaration-id={item.collection.declaration_id} key={item.collection.id}>
                    <div className="portal-card-title">
                      <div><small>{item.collection.id}</small><h4>{item.producer_name} → {item.processing_unit_name}</h4></div>
                      <Proof level="P0">Tournée illustrative</Proof>
                    </div>
                    <p>{item.waste_type_name} · {formatNumber(item.collection.expected_quantity_kg)} kg attendus <Proof level="P1">Déclaré</Proof></p>
                    <div className="portal-route">
                      {item.collection.stops.map((stop) => (
                        <span key={`${item.collection.id}-${stop.order}`}><b>{stop.order}</b><small>{stop.role}</small><strong>{stop.name}</strong><em>{stop.window}</em></span>
                      ))}
                    </div>
                    <p className="route-disclaimer">{item.collection.route_method} · {formatNumber(item.collection.total_straight_line_km)} {item.collection.distance_unit}. Ce n’est pas un itinéraire routier.</p>
                    <dl className="portal-facts inline">
                      <div><dt>Capacité utile</dt><dd>{formatNumber(item.available_capacity_kg)} kg <Proof level="P0">Fictif</Proof></dd></div>
                      <div><dt>Statut</dt><dd>{item.collection.status} <Proof level={item.collection.status_proof_level}>{item.collection.status_provenance}</Proof></dd></div>
                    </dl>
                    {item.collection.status === "assigned" && (
                      <div className="portal-action-form">
                        <label>Justificatif P2 (PDF, JPG ou PNG)<input data-testid="logistics-evidence" type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(event) => setLogisticsFile(event.target.files?.[0] ?? null)} /></label>
                        <label>Masse mesurée P3 (kg)<input data-testid="logistics-weight" type="number" min="1" max="50000" step="0.01" value={measuredQuantity} onChange={(event) => setMeasuredQuantity(event.target.value)} /></label>
                        <button className="primary-button" type="button" disabled={busy} onClick={() => confirmCollectionAndCreateLot(item.collection.id)}>Confirmer collecte, pesée et lot</button>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            )}

            {workspace.actor.role === "processing_unit_operator" && (
              <>
                <div className="portal-grid">
                  {workspace.incoming_lots.length === 0 && <p className="portal-empty">Aucun lot entrant représenté.</p>}
                  {workspace.incoming_lots.map((item) => (
                    <article className="portal-card" data-declaration-id={item.lot.declaration_id} key={item.lot.id}>
                      <div className="portal-card-title"><div><small>{item.lot.id}</small><h4>{item.waste_type_name}</h4></div><Proof level="P3">Entrée mesurée</Proof></div>
                      <p>{item.producer_name} · {formatNumber(item.lot.measured_quantity_kg)} kg</p>
                      <p>Compatibilité catalogue : <strong>{item.compatibility ? "compatible" : "incompatible"}</strong> <Proof level="P0">Règle illustrative</Proof></p>
                      <p>Capacité disponible : {formatNumber(item.available_capacity_kg)} kg <Proof level="P0">Fictive</Proof></p>
                      {item.lot.status === "lot_created" ? (
                        <div className="portal-action-form compact">
                          <label>Décision<select value={decision} onChange={(event) => setDecision(event.target.value as "accepted" | "refused")}><option value="accepted">Accepter</option><option value="refused">Refuser</option></select></label>
                          {decision === "refused" && <label>Motif obligatoire<input value={decisionReason} onChange={(event) => setDecisionReason(event.target.value)} /></label>}
                          <button data-testid="unit-decision" className="primary-button" type="button" disabled={busy || (decision === "refused" && !decisionReason.trim())} onClick={() => decideLot(item.lot.id)}>Enregistrer la décision</button>
                        </div>
                      ) : <strong className="next-action">Décision enregistrée : {item.lot.status}</strong>}
                    </article>
                  ))}
                </div>
                {workspace.projections.map((report) => (
                  <article className="projection-card" key={report.processing_unit_id}>
                    <div className="portal-card-title"><div><small>{report.version} · au {report.as_of}</small><h4>Volumes attendus déclarés et mesurés</h4></div><Proof level="P0">Projection déterministe</Proof></div>
                    <p>{report.source}</p>
                    <div className="projection-grid">
                      {report.periods.map((period) => (
                        <div key={period.period_days}><strong>{period.period_days} jours</strong><span>{formatNumber(period.declared.value_kg)} kg <Proof level="P1">Base déclarée</Proof></span><span>{formatNumber(period.measured_basis.value_kg)} kg <Proof level="P3">Base mesurée</Proof></span><small>Résultat P0 · {period.measured_coverage_declarations} déclaration(s) avec mesure</small></div>
                      ))}
                    </div>
                    <ul>{report.limitations.map((limit) => <li key={limit}>{limit}</li>)}</ul>
                  </article>
                ))}
              </>
            )}

            {workspace.actor.role === "field_controller" && (
              <div className="portal-grid">
                {workspace.pending_controls.length === 0 && <p className="portal-empty">Aucun contrôle en attente.</p>}
                {workspace.pending_controls.map((item) => (
                  <article className="portal-card" data-declaration-id={item.lot.declaration_id} key={item.lot.id}>
                    <div className="portal-card-title"><div><small>{item.lot.id}</small><h4>{item.producer_name}</h4></div><Proof level="P3">À contrôler</Proof></div>
                    <p>{formatNumber(item.lot.measured_quantity_kg)} kg · lot entrant {item.lot.processing_unit_id}</p>
                    <label>Compte rendu du contrôle<textarea value={verificationNote} minLength={3} maxLength={500} onChange={(event) => setVerificationNote(event.target.value)} /></label>
                    <button data-testid="controller-verify" className="primary-button" type="button" disabled={busy || verificationNote.trim().length < 3} onClick={() => verifyLot(item.lot.id)}>Créer l’événement de vérification P4</button>
                    <p className="route-disclaimer">P4 n’est attribué qu’à cet événement explicite, horodaté et signé par le rôle contrôleur.</p>
                  </article>
                ))}
              </div>
            )}

            {workspace.actor.role === "bioloop_coordinator" && (
              <>
                <div className="coordinator-counts">
                  {Object.entries(workspace.coordinator_counts).map(([name, count]) => <div key={name}><strong>{count}</strong><span>{name}</span></div>)}
                </div>
                <div className="coordinator-overview">
                  <article><h4>Déclarations</h4>{workspace.producer_declarations.slice(0, 6).map((item) => <p key={item.declaration.id}><code>{item.declaration.id}</code><span>{item.declaration.producer_name}</span><strong>{item.next_action}</strong></p>)}</article>
                  <article><h4>Collectes</h4>{workspace.logistics_collections.slice(0, 6).map((item) => <p key={item.collection.id}><code>{item.collection.id}</code><span>{item.producer_name} → {item.processing_unit_name}</span><strong>{item.collection.status}</strong></p>)}</article>
                  <article><h4>Lots et décisions</h4>{workspace.incoming_lots.slice(0, 6).map((item) => <p key={item.lot.id}><code>{item.lot.id}</code><span>{item.waste_type_name} · {formatNumber(item.lot.measured_quantity_kg)} kg</span><strong>{item.lot.status}</strong></p>)}</article>
                  <article><h4>Contrôles en attente</h4>{workspace.pending_controls.slice(0, 6).map((item) => <p key={item.lot.id}><code>{item.lot.id}</code><span>{item.producer_name}</span><strong>P4 requis</strong></p>)}</article>
                </div>
                <form className="audit-filters" onSubmit={filterAudit}>
                  {Object.entries(auditFilters).map(([key, value]) => <label key={key}>{key}<input value={value} onChange={(event) => setAuditFilters((current) => ({ ...current, [key]: event.target.value }))} /></label>)}
                  <button className="secondary-button" type="submit" disabled={busy}>Filtrer l’audit</button>
                </form>
                <div className="audit-table" data-testid="coordinator-audit">
                  {(filteredAudit ?? workspace.audit_events).map((event) => (
                    <div key={event.id}><code>{event.correlation_id}</code><strong>{event.event_type}</strong><span>{event.actor_user_id ?? "ancien événement sans acteur"}</span><small>{event.object_type} · {event.object_id}</small></div>
                  ))}
                </div>
              </>
            )}

            {workspace.actor.role === "client_farmer" && (
              <div className="client-empty-state">
                <span>0 produit inventé</span>
                <h4>Aucune disponibilité qualifiée à afficher</h4>
                <p>{workspace.product_empty_state}</p>
                <p>Prochaine tranche : représenter une transformation mesurée, qualifier un produit et publier uniquement le stock réellement disponible.</p>
              </div>
            )}

            <aside className="notification-panel">
              <h4>Notifications internes persistées</h4>
              {workspace.notifications.length === 0 ? <p>Aucune notification pour ce rôle.</p> : workspace.notifications.map((notification) => (
                <div key={notification.id}><strong>{notification.event_type}</strong><span>{notification.message}</span><small>{notification.subject_type} · {notification.subject_id}</small></div>
              ))}
              <small>Aucun email, SMS ou service externe n’est appelé.</small>
            </aside>
          </div>
        )}
      </div>
    </section>
  );
}
