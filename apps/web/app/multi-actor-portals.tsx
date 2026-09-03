"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type {
  AuditEvent,
  AdminAction,
  AdminSession,
  DemoActor,
  DemoRole,
  DemoWorkspace,
  OperationsWorkspace,
  PendingMembership,
  ProductCategory,
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

const productLabels: Record<ProductCategory, string> = {
  measured_biogas: "Biogaz mesuré",
  raw_digestate: "Digestat brut — usage à qualifier",
  liquid_fraction: "Fraction liquide",
  solid_fraction: "Fraction solide",
  compost_amendment: "Compost / amendement à qualifier",
  potential_fertilizing_product: "Produit fertilisant potentiel",
  other_coproduct: "Autre coproduit",
};

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
  const [operations, setOperations] = useState<OperationsWorkspace | null>(null);
  const [pendingMemberships, setPendingMemberships] = useState<PendingMembership[]>([]);
  const [adminHistory, setAdminHistory] = useState<AdminAction[]>([]);
  const [adminSessions, setAdminSessions] = useState<AdminSession[]>([]);
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
  const [demoAvailable, setDemoAvailable] = useState<boolean | null>(null);
  const [outputCategory, setOutputCategory] = useState<ProductCategory>("raw_digestate");
  const [outputQuantity, setOutputQuantity] = useState("500");
  const [outputUnit, setOutputUnit] = useState<"kg" | "L" | "m3">("kg");
  const [outputLocation, setOutputLocation] = useState("Anyama — zone de quarantaine");
  const [qualityValue, setQualityValue] = useState("à confirmer");
  const [reservationQuantity, setReservationQuantity] = useState("25");
  const [clientCategory, setClientCategory] = useState<ProductCategory | "">("");
  const [clientLocation, setClientLocation] = useState("");
  const [clientProof, setClientProof] = useState<"" | "P3" | "P4">("");
  const [adminReason, setAdminReason] = useState("Dossier examiné pour le pilote local.");
  const [invitationEmail, setInvitationEmail] = useState("controleur@example.test");
  const [invitationRole, setInvitationRole] = useState<"field_controller" | "bioloop_coordinator">("field_controller");
  const [invitationToken, setInvitationToken] = useState("");
  const [membershipToRevoke, setMembershipToRevoke] = useState("");
  const [provenanceSummary, setProvenanceSummary] = useState("");

  const refresh = useCallback(async (userId: string) => {
    const [data, operationsData] = await Promise.all([
      api.demoWorkspace(userId),
      api.operationsWorkspace(userId),
    ]);
    setWorkspace(data);
    setOperations(operationsData);
    if (data.actor.role === "bioloop_coordinator") {
      const [pending, history, sessions] = await Promise.all([
        api.pendingMemberships(userId),
        api.adminHistory(userId),
        api.activeAdminSessions(userId),
      ]);
      setPendingMemberships(pending);
      setAdminHistory(history);
      setAdminSessions(sessions);
    } else {
      setPendingMemberships([]);
      setAdminHistory([]);
      setAdminSessions([]);
    }
    onActorChange(data.actor);
  }, [onActorChange]);

  useEffect(() => {
    api.demoActors()
      .then((catalog) => {
        setDemoAvailable(true);
        setActors(catalog.actors);
        return refresh(selectedUserId);
      })
      .catch((reason: Error) => {
        if (reason instanceof ApiError && reason.status === 404) {
          setDemoAvailable(false);
          onActorChange(null);
          return;
        }
        setError(reason.message);
      });
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

  const createTransformation = (lot: OperationsWorkspace["accepted_lots"][number]) => run(() =>
    api.createTransformation(
      {
        processing_unit_id: lot.processing_unit_id,
        process: "Transformation pilote — procédé déclaré par l’opérateur",
        started_at: new Date().toISOString(),
        inputs: [{
          lot_id: lot.id,
          measured_quantity: lot.measured_quantity_kg,
          unit: "kg",
          measurement_method: "balance de réception unité",
          measured_at: new Date().toISOString(),
          evidence_ids: lot.evidence_ids,
        }],
      },
      selectedUserId,
    ),
  );

  const createOutput = (transformationId: string) => run(() =>
    api.createProductOutputs(
      transformationId,
      [{
        category: outputCategory,
        quantity: outputQuantity,
        unit: outputUnit,
        measurement_method: "mesure saisie par l’opérateur",
        measured_at: new Date().toISOString(),
        evidence_id: operations?.transformations.find(
          (item) => item.id === transformationId,
        )?.evidence_ids[0],
        location: outputLocation,
      }],
      selectedUserId,
    ),
  );

  const addQuality = (productId: string) => run(() =>
    api.addQualityTest(
      productId,
      {
        parameter: "Contrôle qualité déclaré",
        value: qualityValue,
        unit: "valeur déclarée",
        method: "contrôle local documenté — non certifié",
        laboratory_or_actor: workspace?.actor.organization_name ?? "Acteur de contrôle",
        tested_at: new Date().toISOString(),
      },
      selectedUserId,
    ),
  );

  const releaseProduct = (productId: string) => run(() =>
    api.releaseProduct(
      productId,
      {
        status: "released",
        note: "Libération interne P4 pour disponibilité ; aucune certification P5.",
      },
      selectedUserId,
    ),
  );

  const reserveProduct = (productId: string, unit: "kg" | "L" | "m3") => run(() =>
    api.reserveProduct(
      productId,
      {
        quantity: reservationQuantity,
        unit,
        idempotency_key: `portal:${productId}:${Date.now()}`,
      },
      selectedUserId,
    ),
  );

  const decideMembership = (
    membership: PendingMembership,
    decision: "approved" | "refused",
  ) => run(() => api.decideMembership(
    membership.id,
    {
      decision,
      reason: adminReason,
      ...(decision === "approved" && membership.organization_kind === "processing_unit"
        ? { processing_unit_id: "UNIT-001" }
        : {}),
    },
    selectedUserId,
  ));

  const inviteSensitiveRole = () => run(async () => {
    const invitation = await api.createInvitation(
      {
        email: invitationEmail,
        role: invitationRole,
        organization_name: invitationRole === "field_controller"
          ? "Contrôle pilote local"
          : "Coordination BioLoop pilote",
        expires_in_hours: 24,
      },
      selectedUserId,
    );
    setInvitationToken(invitation.token);
  });

  const revokeMembership = () => run(async () => {
    await api.revokeMembership(membershipToRevoke, adminReason, selectedUserId);
    setMembershipToRevoke("");
  });

  const showProvenance = async (productId: string) => {
    setBusy(true);
    setError("");
    try {
      const payload = await api.productProvenance(productId, selectedUserId);
      const inputs = Array.isArray(payload.declarations_to_inputs)
        ? payload.declarations_to_inputs as Array<Record<string, unknown>>
        : [];
      const evidence = Array.isArray(payload.evidence)
        ? payload.evidence as Array<Record<string, unknown>>
        : [];
      const transformation = payload.transformation as Record<string, unknown> | undefined;
      const quality = Array.isArray(payload.quality_controls)
        ? payload.quality_controls as Array<Record<string, unknown>>
        : [];
      const movements = Array.isArray(payload.inventory_movements)
        ? payload.inventory_movements as Array<Record<string, unknown>>
        : [];
      const reservations = Array.isArray(payload.reservations)
        ? payload.reservations as Array<Record<string, unknown>>
        : [];
      const source = inputs[0] ?? {};
      setProvenanceSummary([
        `déclaration ${String(source.declaration_id ?? "—")}`,
        `preuve ${String(evidence[0]?.id ?? "—")} (P2)`,
        `mesure ${String(source.measurement_id ?? "—")} (P3)`,
        `collecte ${String(source.collection_id ?? "—")}`,
        `lot entrant ${String(source.lot_id ?? "—")}`,
        `transformation ${String(transformation?.id ?? "—")}`,
        `lot produit ${productId} (P3)`,
        `contrôle qualité ${String(quality[0]?.id ?? "—")} (P4 si vérifié)`,
        `stock ${String(movements.length)} mouvement(s)`,
        `réservation ${String(reservations[0]?.id ?? "aucune")}`,
      ].join(" → "));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Erreur inattendue");
    } finally {
      setBusy(false);
    }
  };

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

  if (demoAvailable === false) return null;

  const clientProducts = (operations?.products ?? []).filter((product) =>
    (!clientCategory || product.category === clientCategory)
    && (!clientLocation || product.location.toLocaleLowerCase("fr").includes(clientLocation.toLocaleLowerCase("fr")))
    && (!clientProof || product.proof_level === clientProof || product.release_proof_level === clientProof)
  );

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
                <section className="slice05-panel" data-testid="transformation-workspace">
                  <div className="portal-card-title">
                    <div><small>Tranche 05 · mesures physiques</small><h4>Transformer et enregistrer les sorties</h4></div>
                    <Proof level="P3">Saisie opérateur</Proof>
                  </div>
                  <p className="route-disclaimer">Aucune quantité n’est produite depuis les URI illustratives. Entrées, pertes et sorties sont enregistrées séparément avec leur unité.</p>
                  <div className="portal-grid">
                    {operations?.accepted_lots.map((lot) => (
                      <article className="portal-card" key={lot.id} data-lot-id={lot.id}>
                        <small>{lot.id}</small>
                        <h4>Lot accepté disponible</h4>
                        <p>{formatNumber(lot.measured_quantity_kg)} kg · {lot.waste_type_id}</p>
                        <button data-testid="create-transformation" className="primary-button" type="button" disabled={busy} onClick={() => createTransformation(lot)}>Démarrer la transformation mesurée</button>
                      </article>
                    ))}
                    {operations?.transformations.map((transformation) => (
                      <article className="portal-card" key={transformation.id} data-transformation-id={transformation.id}>
                        <small>{transformation.id}</small>
                        <h4>{transformation.process}</h4>
                        <p>{transformation.inputs.length} lot(s) · statut <strong>{transformation.status}</strong></p>
                        <p>{transformation.measurement_warning}</p>
                        <div className="portal-action-form compact">
                          <label>Catégorie<select data-testid="output-category" value={outputCategory} onChange={(event) => setOutputCategory(event.target.value as ProductCategory)}>{Object.entries(productLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
                          <label>Quantité mesurée<input data-testid="output-quantity" type="number" min="0.001" step="0.001" value={outputQuantity} onChange={(event) => setOutputQuantity(event.target.value)} /></label>
                          <label>Unité<select value={outputUnit} onChange={(event) => setOutputUnit(event.target.value as "kg" | "L" | "m3")}><option value="kg">kg</option><option value="L">L</option><option value="m3">m³</option></select></label>
                          <label>Localisation<input value={outputLocation} onChange={(event) => setOutputLocation(event.target.value)} /></label>
                          <button data-testid="create-product-output" className="primary-button" type="button" disabled={busy || Number(outputQuantity) <= 0} onClick={() => createOutput(transformation.id)}>Enregistrer cette sortie physique</button>
                        </div>
                      </article>
                    ))}
                    {operations?.products.map((product) => (
                      <article className="portal-card product-card" key={product.id}>
                        <small>{product.id}</small>
                        <h4>{productLabels[product.category]}</h4>
                        <p>{formatNumber(product.quantity)} {product.unit} · {product.measurement_method}</p>
                        <p>Stock dérivé : {formatNumber(product.available_quantity)} {product.unit} disponibles</p>
                        <Proof level={product.proof_level}>Sortie mesurée</Proof>
                        <strong className="next-action">Qualité : {product.quality_status}</strong>
                      </article>
                    ))}
                  </div>
                </section>
              </>
            )}

            {workspace.actor.role === "field_controller" && (
              <>
                <div className="portal-grid">
                  {workspace.pending_controls.length === 0 && <p className="portal-empty">Aucun contrôle d’intrant en attente.</p>}
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
                <section className="slice05-panel" data-testid="quality-workspace">
                  <div className="portal-card-title"><div><small>Qualité et libération</small><h4>Produits en quarantaine ou en analyse</h4></div><Proof level="P4">Contrôle explicite</Proof></div>
                  <p className="route-disclaimer">Une libération P4 autorise la disponibilité interne ; elle ne crée aucune certification P5 et ne transforme pas automatiquement un digestat en engrais.</p>
                  <label className="quality-value-field">Valeur ou conclusion du contrôle<input value={qualityValue} onChange={(event) => setQualityValue(event.target.value)} /></label>
                  <div className="portal-grid">
                    {operations?.products.length === 0 && <p className="portal-empty">Aucun lot produit à contrôler.</p>}
                    {operations?.products.map((product) => (
                      <article className="portal-card product-card" key={product.id} data-product-id={product.id}>
                        <small>{product.id}</small>
                        <h4>{productLabels[product.category]}</h4>
                        <p>{formatNumber(product.quantity)} {product.unit} · {product.location}</p>
                        <strong className="next-action">{product.quality_status}</strong>
                        {product.quality_status === "quarantine" && <button data-testid="add-quality-test" className="secondary-button" type="button" disabled={busy} onClick={() => addQuality(product.id)}>Enregistrer le contrôle qualité</button>}
                        {product.quality_status === "pending_analysis" && <button data-testid="release-product" className="primary-button" type="button" disabled={busy} onClick={() => releaseProduct(product.id)}>Libérer en P4 — non certifié P5</button>}
                      </article>
                    ))}
                  </div>
                </section>
              </>
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
                <section className="slice05-panel admin-panel" data-testid="admin-workspace">
                  <div className="portal-card-title"><div><small>Administration pilote</small><h4>Valider les organisations et inviter les rôles sensibles</h4></div><Proof level="P1">Décision auditée</Proof></div>
                  <label>Motif de décision<input data-testid="admin-reason" value={adminReason} onChange={(event) => setAdminReason(event.target.value)} /></label>
                  <div className="portal-grid">
                    {pendingMemberships.length === 0 && <p className="portal-empty">Aucune inscription logistique ou unité en attente.</p>}
                    {pendingMemberships.map((membership) => (
                      <article className="portal-card" key={membership.id}>
                        <small>{membership.id}</small>
                        <h4>{membership.organization_name}</h4>
                        <p>{membership.display_name} · {membership.organization_kind}</p>
                        <div className="admin-actions">
                          <button data-testid="approve-membership" className="primary-button" type="button" disabled={busy} onClick={() => decideMembership(membership, "approved")}>Approuver</button>
                          <button data-testid="refuse-membership" className="secondary-button" type="button" disabled={busy || adminReason.trim().length < 3} onClick={() => decideMembership(membership, "refused")}>Refuser avec motif</button>
                        </div>
                      </article>
                    ))}
                  </div>
                  <div className="portal-action-form admin-invitation-form">
                    <label>Email invité<input data-testid="invitation-email" type="email" value={invitationEmail} onChange={(event) => setInvitationEmail(event.target.value)} /></label>
                    <label>Rôle sensible<select value={invitationRole} onChange={(event) => setInvitationRole(event.target.value as "field_controller" | "bioloop_coordinator")}><option value="field_controller">Contrôleur terrain</option><option value="bioloop_coordinator">Coordinateur</option></select></label>
                    <button data-testid="create-invitation" className="primary-button" type="button" disabled={busy} onClick={inviteSensitiveRole}>Créer l’invitation locale 24 h</button>
                    {invitationToken && <p className="local-token"><strong>Jeton affiché une seule fois :</strong> <code>{invitationToken}</code><br />Seule son empreinte SHA-256 est stockée. Aucun email externe n’est envoyé.</p>}
                  </div>
                  <div className="admin-revocation-grid">
                    <div className="portal-action-form compact">
                      <label>Appartenance à révoquer<input data-testid="membership-to-revoke" value={membershipToRevoke} placeholder="PMEM-…" onChange={(event) => setMembershipToRevoke(event.target.value)} /></label>
                      <button data-testid="revoke-membership" className="secondary-button" type="button" disabled={busy || membershipToRevoke.trim().length < 5 || adminReason.trim().length < 3} onClick={revokeMembership}>Révoquer l’appartenance et ses sessions</button>
                    </div>
                    <div className="admin-session-list">
                      <h4>Sessions actives du pilote</h4>
                      {adminSessions.length === 0 && <p>Aucune session active.</p>}
                      {adminSessions.slice(0, 8).map((session) => (
                        <article key={session.id}>
                          <div><strong>{session.display_name}</strong><code>{session.id}</code><small>{session.active_membership_id}</small></div>
                          <button data-testid="revoke-session" className="secondary-button" type="button" disabled={busy || adminReason.trim().length < 3} onClick={() => run(() => api.revokeAdminSession(session.id, adminReason, selectedUserId))}>Révoquer la session</button>
                        </article>
                      ))}
                    </div>
                  </div>
                  <div className="audit-table admin-history">
                    {adminHistory.slice(0, 8).map((event) => <div key={event.id}><code>{event.correlation_id}</code><strong>{event.action}</strong><span>{event.decision ?? "action"}</span><small>{event.subject_type} · {event.subject_id}</small></div>)}
                  </div>
                </section>
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
              <section className="slice05-panel client-product-panel" data-testid="client-product-workspace">
                <div className="portal-card-title"><div><small>Disponibilités mesurées et libérées</small><h4>Produits accessibles au client</h4></div><Proof level="P4">Libération interne</Proof></div>
                <p className="route-disclaimer">Seuls les produits `released` avec un stock disponible dérivé du registre sont publiés. Aucune vente ni certification P5.</p>
                <div className="client-product-filters" aria-label="Filtres des produits disponibles">
                  <label>Catégorie<select data-testid="client-category-filter" value={clientCategory} onChange={(event) => setClientCategory(event.target.value as ProductCategory | "")}><option value="">Toutes</option>{Object.entries(productLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
                  <label>Localisation<input data-testid="client-location-filter" value={clientLocation} placeholder="Ex. Anyama" onChange={(event) => setClientLocation(event.target.value)} /></label>
                  <label>Niveau de preuve<select data-testid="client-proof-filter" value={clientProof} onChange={(event) => setClientProof(event.target.value as "" | "P3" | "P4")}><option value="">Tous</option><option value="P3">P3 — quantité mesurée</option><option value="P4">P4 — libération interne</option></select></label>
                </div>
                {(operations?.products.length ?? 0) === 0 ? (
                  <div className="client-empty-state">
                    <span>0 produit inventé</span>
                    <h4>Aucune disponibilité qualifiée à afficher</h4>
                    <p>{workspace.product_empty_state}</p>
                  </div>
                ) : (
                  <>
                    <label>Quantité à réserver<input data-testid="reservation-quantity" type="number" min="0.001" step="0.001" value={reservationQuantity} onChange={(event) => setReservationQuantity(event.target.value)} /></label>
                    <div className="portal-grid">
                      {clientProducts.map((product) => (
                        <article className="portal-card product-card" key={product.id} data-product-id={product.id}>
                          <small>{product.id}</small>
                          <h4>{productLabels[product.category]}</h4>
                          <p><strong>{formatNumber(product.available_quantity)} {product.unit}</strong> disponibles à {product.location}</p>
                          <p>Mesure : {product.measurement_method} · <Proof level="P3">Quantité</Proof> <Proof level="P4">Libéré</Proof></p>
                          <p>{product.quality_warning}</p>
                          <button data-testid="reserve-product" className="primary-button" type="button" disabled={busy || Number(reservationQuantity) <= 0} onClick={() => reserveProduct(product.id, product.unit)}>Réserver sans paiement</button>
                          <button className="secondary-button" type="button" disabled={busy} onClick={() => showProvenance(product.id)}>Voir la chaîne de provenance</button>
                        </article>
                      ))}
                      {clientProducts.length === 0 && <p className="portal-empty">Aucun produit ne correspond à ces filtres.</p>}
                    </div>
                  </>
                )}
                {provenanceSummary && <p className="provenance-chain" data-testid="provenance-chain">{provenanceSummary}</p>}
                <div className="reservation-list">
                  {operations?.reservations.map((reservation) => (
                    <article key={reservation.id}>
                      <code>{reservation.id}</code>
                      <span>{formatNumber(reservation.quantity)} {reservation.unit} · {reservation.status}</span>
                      {reservation.status === "active" && <button data-testid="cancel-reservation" className="secondary-button" type="button" disabled={busy} onClick={() => run(() => api.cancelReservation(reservation.id, selectedUserId))}>Annuler ma réservation</button>}
                    </article>
                  ))}
                </div>
              </section>
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
