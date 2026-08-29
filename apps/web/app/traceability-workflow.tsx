"use client";

import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type {
  Declaration,
  DeclarationTimeline,
  EvidenceRecord,
  LotDecision,
  LotRecord,
  MeasurementRecord,
  Proposal,
  RecalculationResult,
} from "@/lib/types";

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const ALLOWED_FILE_TYPES = ["image/jpeg", "image/png", "application/pdf"];

const formatNumber = (value: string | number, digits = 0) =>
  new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(Number(value));

const localDateTimeValue = () => {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
};

function ProofBadge({ level, label }: { level: string; label: string }) {
  return (
    <span className={`evidence evidence-${level.toLowerCase()}`}>
      <strong>{level}</strong> {label}
    </span>
  );
}

export function TraceabilityWorkflow({
  declaration,
  proposal,
}: {
  declaration: Declaration;
  proposal: Proposal;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [evidenceCategory, setEvidenceCategory] =
    useState<EvidenceRecord["category"]>("photo_gisement");
  const [capturedDate, setCapturedDate] = useState("");
  const [evidenceNote, setEvidenceNote] = useState("");
  const [evidence, setEvidence] = useState<EvidenceRecord | null>(null);
  const [measuredQuantity, setMeasuredQuantity] = useState(declaration.quantity_kg);
  const [measurementMethod, setMeasurementMethod] =
    useState<MeasurementRecord["method"]>("balance_mobile");
  const [measuredAt, setMeasuredAt] = useState(localDateTimeValue());
  const [deviceReference, setDeviceReference] = useState("BAL-DEMO-01");
  const [measurementNote, setMeasurementNote] = useState("");
  const [measurement, setMeasurement] = useState<MeasurementRecord | null>(null);
  const [lot, setLot] = useState<LotRecord | null>(null);
  const [decisionKind, setDecisionKind] = useState<"accepted" | "refused">("accepted");
  const [decisionReason, setDecisionReason] = useState("");
  const [decisionNote, setDecisionNote] = useState("");
  const [decision, setDecision] = useState<LotDecision | null>(null);
  const [recalculation, setRecalculation] = useState<RecalculationResult | null>(null);
  const [timeline, setTimeline] = useState<DeclarationTimeline | null>(null);
  const [busyStep, setBusyStep] = useState("");
  const [error, setError] = useState("");

  const refreshTimeline = async () => {
    setTimeline(await api.timeline(declaration.id));
  };

  useEffect(() => {
    setFile(null);
    setEvidence(null);
    setMeasuredQuantity(declaration.quantity_kg);
    setMeasuredAt(localDateTimeValue());
    setMeasurement(null);
    setLot(null);
    setDecision(null);
    setRecalculation(null);
    setError("");
    api.timeline(declaration.id).then(setTimeline).catch(() => setTimeline(null));
  }, [declaration.id, declaration.quantity_kg]);

  const submitEvidence = async (event: FormEvent) => {
    event.preventDefault();
    if (!file) {
      setError("Sélectionnez une pièce JPEG, PNG ou PDF.");
      return;
    }
    if (!ALLOWED_FILE_TYPES.includes(file.type) || file.size > MAX_FILE_BYTES) {
      setError("La pièce doit être un JPEG, PNG ou PDF de 5 Mo maximum.");
      return;
    }
    setBusyStep("evidence");
    setError("");
    try {
      const created = await api.createEvidence(declaration.id, file, {
        category: evidenceCategory,
        captured_at: capturedDate
          ? new Date(`${capturedDate}T00:00:00`).toISOString()
          : undefined,
        note: evidenceNote,
      });
      setEvidence(created);
      await refreshTimeline();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Erreur inattendue");
    } finally {
      setBusyStep("");
    }
  };

  const submitMeasurement = async (event: FormEvent) => {
    event.preventDefault();
    setBusyStep("measurement");
    setError("");
    try {
      const created = await api.createMeasurement(declaration.id, {
        quantity_kg: measuredQuantity,
        unit: "kg",
        method: measurementMethod,
        measured_at: new Date(measuredAt).toISOString(),
        device_reference: deviceReference || null,
        evidence_id: evidence?.id ?? null,
        supersedes_measurement_id: measurement?.id ?? null,
        note: measurementNote,
      });
      setMeasurement(created);
      await refreshTimeline();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Erreur inattendue");
    } finally {
      setBusyStep("");
    }
  };

  const createLot = async () => {
    if (!measurement) return;
    setBusyStep("lot");
    setError("");
    try {
      const created = await api.createLot(declaration.id, {
        measurement_id: measurement.id,
        processing_unit_id: proposal.selected_unit.id,
        evidence_ids: evidence ? [evidence.id] : [],
      });
      setLot(created);
      await refreshTimeline();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Erreur inattendue");
    } finally {
      setBusyStep("");
    }
  };

  const submitDecision = async (event: FormEvent) => {
    event.preventDefault();
    if (!lot) return;
    setBusyStep("decision");
    setError("");
    try {
      const created = await api.decideLot(lot.id, {
        decision: decisionKind,
        reason: decisionReason,
        note: decisionNote,
      });
      setDecision(created);
      setLot({ ...lot, status: created.decision, decision: created });
      await refreshTimeline();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Erreur inattendue");
    } finally {
      setBusyStep("");
    }
  };

  const recalculate = async () => {
    if (!measurement) return;
    setBusyStep("recalculation");
    setError("");
    try {
      setRecalculation(
        await api.recalculate(
          declaration.id,
          measurement.id,
          proposal.selected_unit.id,
        ),
      );
      await refreshTimeline();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Erreur inattendue");
    } finally {
      setBusyStep("");
    }
  };

  const difference = measurement
    ? Number(measurement.quantity_kg) - Number(declaration.quantity_kg)
    : null;
  const timelineLot = timeline?.lots.find((item) => item.id === lot?.id) ?? lot;

  return (
    <section className="traceability-section" data-testid="traceability-workflow" aria-labelledby="traceability-title">
      <div className="section-shell">
        <div className="section-heading light">
          <div>
            <span className="section-index">04</span>
            <h2 id="traceability-title">Documenter, mesurer, décider</h2>
          </div>
          <p>
            La preuve P2 et la mesure P3 renforcent l’entrée. Elles ne transforment
            ni la décision de démonstration en P4, ni les sorties illustratives en mesure.
          </p>
        </div>

        <div className="trace-steps">
          <form className="trace-card" onSubmit={submitEvidence}>
            <div className="trace-card-title"><span>1</span><div><small>DOCUMENTÉ</small><h3>Documenter — P2</h3></div><ProofBadge level="P2" label="Pièce fournie" /></div>
            <label>
              Photo ou document
              <input
                data-testid="evidence-file"
                type="file"
                accept="image/jpeg,image/png,application/pdf"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                required={!evidence}
              />
            </label>
            <div className="form-row">
              <label>
                Catégorie
                <select value={evidenceCategory} onChange={(event) => setEvidenceCategory(event.target.value as EvidenceRecord["category"])}>
                  <option value="photo_gisement">Photo du gisement</option>
                  <option value="bon_pesee">Bon de pesée</option>
                  <option value="document_accompagnement">Document d’accompagnement</option>
                  <option value="autre">Autre preuve</option>
                </select>
              </label>
              <label>
                Date de capture déclarée
                <input type="date" value={capturedDate} onChange={(event) => setCapturedDate(event.target.value)} />
              </label>
            </div>
            <label>
              Note facultative
              <textarea maxLength={500} value={evidenceNote} onChange={(event) => setEvidenceNote(event.target.value)} />
            </label>
            <p className="security-note">JPEG, PNG ou PDF · 5 Mo maximum · EXIF non vérifié · aucune géolocalisation publiée.</p>
            <button data-testid="upload-evidence" className="primary-button full" disabled={busyStep === "evidence" || Boolean(evidence)}>
              {evidence ? "Preuve P2 enregistrée" : busyStep === "evidence" ? "Contrôle…" : "Ajouter la preuve"}
            </button>
            {evidence && (
              <div className="record-summary" data-testid="evidence-summary">
                <strong>{evidence.original_filename}</strong>
                <span>{formatNumber(evidence.size_bytes)} octets · SHA-256</span>
                <code>{evidence.sha256}</code>
              </div>
            )}
          </form>

          <form className="trace-card" onSubmit={submitMeasurement}>
            <div className="trace-card-title"><span>2</span><div><small>MESURÉ</small><h3>Mesurer — P3</h3></div><ProofBadge level="P3" label="Pesée saisie" /></div>
            <div className="form-row">
              <label>
                Masse mesurée (kg)
                <input data-testid="measured-quantity" type="number" min="0.01" max="50000" step="0.01" value={measuredQuantity} onChange={(event) => setMeasuredQuantity(event.target.value)} required />
              </label>
              <label>
                Méthode
                <select value={measurementMethod} onChange={(event) => setMeasurementMethod(event.target.value as MeasurementRecord["method"])}>
                  <option value="balance_mobile">Balance mobile</option>
                  <option value="balance_plateforme">Balance plateforme</option>
                  <option value="balance_mecanique">Balance mécanique</option>
                  <option value="autre">Autre méthode</option>
                </select>
              </label>
            </div>
            <div className="form-row">
              <label>
                Date et heure de mesure
                <input type="datetime-local" value={measuredAt} onChange={(event) => setMeasuredAt(event.target.value)} required />
              </label>
              <label>
                Référence appareil
                <input maxLength={100} value={deviceReference} onChange={(event) => setDeviceReference(event.target.value)} />
              </label>
            </div>
            <label>
              Note facultative
              <textarea maxLength={500} value={measurementNote} onChange={(event) => setMeasurementNote(event.target.value)} />
            </label>
            <p className="security-note">Une correction crée une nouvelle mesure. P3 n’est ni P4 vérifié ni P5 certifié.</p>
            <button data-testid="record-measurement" className="primary-button full" disabled={busyStep === "measurement" || Boolean(lot)}>
              {busyStep === "measurement" ? "Enregistrement…" : measurement ? "Créer une mesure de correction" : "Enregistrer la mesure P3"}
            </button>
            {measurement && (
              <div className="record-summary" data-testid="measurement-summary">
                <strong>{formatNumber(measurement.quantity_kg, 2)} kg</strong>
                <span>{measurement.id} · {measurement.method.replaceAll("_", " ")}</span>
                {measurement.supersedes_measurement_id && <small>Corrige sans effacer {measurement.supersedes_measurement_id}</small>}
              </div>
            )}
          </form>

          <article className="trace-card action-card">
            <div className="trace-card-title"><span>3</span><div><small>TRAÇABILITÉ</small><h3>Créer le lot</h3></div><ProofBadge level="P3" label="Entrée mesurée" /></div>
            <dl className="compact-list">
              <div><dt>Déclaration</dt><dd>{declaration.id}</dd></div>
              <div><dt>Mesure source</dt><dd>{measurement?.id ?? "En attente"}</dd></div>
              <div><dt>Unité sélectionnée</dt><dd>{proposal.selected_unit.name}</dd></div>
              <div><dt>Masse du lot</dt><dd>{measurement ? `${formatNumber(measurement.quantity_kg, 2)} kg` : "En attente"}</dd></div>
            </dl>
            <button data-testid="create-lot" className="primary-button full" type="button" onClick={createLot} disabled={!measurement || Boolean(lot) || busyStep === "lot"}>
              {lot ? "Lot créé" : busyStep === "lot" ? "Création…" : "Créer depuis cette mesure"}
            </button>
            {lot && (
              <div className="record-summary" data-testid="lot-summary">
                <strong>{lot.id}</strong>
                <span>{formatNumber(lot.measured_quantity_kg, 2)} kg · statut {lot.status}</span>
              </div>
            )}
          </article>

          <form className="trace-card" onSubmit={submitDecision}>
            <div className="trace-card-title"><span>4</span><div><small>DÉCISION DÉMO</small><h3>Accepter ou refuser</h3></div><ProofBadge level="P1" label="Non authentifié" /></div>
            <label>
              Décision de l’unité
              <select data-testid="decision-kind" value={decisionKind} onChange={(event) => setDecisionKind(event.target.value as "accepted" | "refused")} disabled={Boolean(decision)}>
                <option value="accepted">Accepter le lot</option>
                <option value="refused">Refuser le lot</option>
              </select>
            </label>
            {decisionKind === "refused" && (
              <label>
                Motif du refus
                <textarea data-testid="decision-reason" maxLength={500} value={decisionReason} onChange={(event) => setDecisionReason(event.target.value)} required />
              </label>
            )}
            <label>
              Note facultative
              <textarea maxLength={500} value={decisionNote} onChange={(event) => setDecisionNote(event.target.value)} />
            </label>
            <div className="demo-warning">Acteur : opérateur unité de démonstration non authentifié. Cet événement n’est pas une vérification P4.</div>
            <button data-testid="record-decision" className="primary-button full" disabled={!lot || Boolean(decision) || busyStep === "decision"}>
              {decision ? "Décision enregistrée" : busyStep === "decision" ? "Enregistrement…" : "Enregistrer la décision"}
            </button>
            {decision && (
              <div className="record-summary" data-testid="decision-summary">
                <strong>{decision.decision === "accepted" ? "Lot accepté" : "Lot refusé"}</strong>
                <span>{decision.actor_label}</span>
              </div>
            )}
          </form>
        </div>

        <div className="comparison-panel" data-testid="mass-comparison">
          <div>
            <small>MASSE DÉCLARÉE</small>
            <strong>{formatNumber(declaration.quantity_kg, 2)} kg</strong>
            <ProofBadge level="P1" label="Déclaré" />
          </div>
          <span className="comparison-arrow">→</span>
          <div>
            <small>MASSE MESURÉE</small>
            <strong>{measurement ? `${formatNumber(measurement.quantity_kg, 2)} kg` : "En attente"}</strong>
            <ProofBadge level="P3" label="Mesuré" />
          </div>
          <div className="delta-box">
            <small>ÉCART</small>
            <strong>{difference === null ? "—" : `${difference >= 0 ? "+" : ""}${formatNumber(difference, 2)} kg`}</strong>
          </div>
          <button data-testid="recalculate-estimate" className="primary-button" type="button" onClick={recalculate} disabled={!measurement || !decision || Boolean(recalculation) || busyStep === "recalculation"}>
            {recalculation ? "Recalcul conservé" : busyStep === "recalculation" ? "Recalcul…" : "Recalculer depuis P3"}
          </button>
        </div>

        {recalculation && (
          <div className="recalculation-panel" data-testid="recalculation-results">
            <div className="illustrative-alert">
              <ProofBadge level="P0" label="Sorties illustratives" />
              <div><strong>L’entrée est P3 ; les résultats restent P0.</strong><p>Même jeu de facteurs illustratif, nouvelle exécution immuable, aucune conversion physique ou économique.</p></div>
            </div>
            <div className="scenario-grid">
              {recalculation.estimate.scenarios.map((scenario) => (
                <article className={`scenario-card scenario-${scenario.key}`} key={scenario.key}>
                  <span>SCÉNARIO {scenario.label.toUpperCase()}</span>
                  <strong>{formatNumber(scenario.value, 2)}</strong>
                  <p>{recalculation.estimate.output_unit}</p>
                  <small>{formatNumber(recalculation.estimate.input_quantity_kg, 2)} kg P3 × {scenario.multiplier_uri_per_kg} URI/kg P0</small>
                </article>
              ))}
            </div>
            <dl className="lineage-list">
              <div><dt>Exécution conservée</dt><dd>{recalculation.previous_estimate.id}</dd></div>
              <div><dt>Nouvelle exécution</dt><dd>{recalculation.estimate.id}</dd></div>
              <div><dt>Mesure source</dt><dd>{recalculation.lineage.source_measurement_id}</dd></div>
              <div><dt>Nouvelle empreinte</dt><dd><code>{recalculation.estimate.calculation_hash}</code></dd></div>
            </dl>
          </div>
        )}

        <article className="timeline-panel" data-testid="timeline">
          <div className="result-card-heading">
            <div><span className="card-number">J</span><h3>Chaîne de provenance et journal</h3></div>
            <span className="event-count">{timeline?.audit_events.length ?? 0} événements</span>
          </div>
          <div className="provenance-chain" data-testid="provenance-chain">
            <span><ProofBadge level="P1" label="Déclaration" /><small>{declaration.id}</small></span>
            <i>→</i>
            <span><ProofBadge level="P2" label="Preuve" /><small>{evidence?.id ?? "en attente"}</small></span>
            <i>→</i>
            <span><ProofBadge level="P3" label="Mesure" /><small>{measurement?.id ?? "en attente"}</small></span>
            <i>→</i>
            <span><ProofBadge level="P0" label="Recalcul" /><small>{recalculation?.estimate.id ?? "en attente"}</small></span>
          </div>
          {timelineLot && (
            <div className="status-history" data-testid="lot-status-history">
              {timelineLot.status_history.map((event) => (
                <span key={event.id}><strong>{event.status}</strong><small>{event.actor_label}</small></span>
              ))}
            </div>
          )}
          <div className="timeline-list">
            {(timeline?.audit_events ?? []).map((event) => (
              <div className="timeline-event" key={event.id}>
                <span />
                <div><strong>{event.event_type}</strong><small>{event.object_id} · {new Date(event.created_at).toLocaleString("fr-FR")}</small></div>
                <code>{event.correlation_id}</code>
              </div>
            ))}
          </div>
          <p className="security-note">Le journal conserve les identifiants et métadonnées utiles, jamais le contenu binaire des pièces.</p>
        </article>

        {error && <div className="error-banner trace-error" role="alert">{error}</div>}
      </div>
    </section>
  );
}
