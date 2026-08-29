"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { TraceabilityWorkflow } from "./traceability-workflow";
import type {
  Catalog,
  Declaration,
  ProcessingUnit,
  Proposal,
  UnitMatch,
} from "@/lib/types";

const formatNumber = (value: string | number, digits = 0) =>
  new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(Number(value));

const evidenceDescriptions: Record<string, string> = {
  P0: "Donnée fictive ou résultat de simulation",
  P1: "Saisie déclarative, sans mesure indépendante",
  P2: "Pièce ou historique associé",
  P3: "Mesure avec métadonnées",
  P4: "Contrôle par un acteur autorisé",
  P5: "Méthode et organisme reconnus",
};

function EvidenceBadge({ level, label }: { level: string; label?: string }) {
  return (
    <span className={`evidence evidence-${level.toLowerCase()}`} title={evidenceDescriptions[level]}>
      <strong>{level}</strong> {label ?? evidenceDescriptions[level]}
    </span>
  );
}

function UnitCard({ unit, catalog }: { unit: ProcessingUnit; catalog: Catalog }) {
  const available = Number(unit.daily_capacity_kg) - Number(unit.reserved_capacity_kg);
  const wasteNames = unit.accepted_waste_type_ids
    .map((id) => catalog.waste_types.find((waste) => waste.id === id)?.name)
    .filter(Boolean);
  return (
    <article className="catalog-card unit-card">
      <div className="card-heading">
        <span className="icon-block">UT</span>
        <EvidenceBadge level={unit.proof_level} label="Unité fictive" />
      </div>
      <h3>{unit.name}</h3>
      <p>{unit.process}</p>
      <dl className="mini-stats">
        <div>
          <dt>Localité</dt>
          <dd>{unit.locality}</dd>
        </div>
        <div>
          <dt>Capacité dispo.</dt>
          <dd>{formatNumber(available)} kg/j</dd>
        </div>
      </dl>
      <p className="accepted">Accepte : {wasteNames.join(" · ")}</p>
    </article>
  );
}

export default function Home() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [declaration, setDeclaration] = useState<Declaration | null>(null);
  const [matches, setMatches] = useState<UnitMatch[]>([]);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [producerId, setProducerId] = useState("");
  const [wasteTypeId, setWasteTypeId] = useState("");
  const [quantity, setQuantity] = useState("1500");
  const [frequency, setFrequency] = useState("hebdomadaire");
  const [availabilityDate, setAvailabilityDate] = useState("");
  const [notes, setNotes] = useState("");
  const [selectedUnitId, setSelectedUnitId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const tomorrow = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10);
    setAvailabilityDate(tomorrow);
    api
      .catalog()
      .then((data) => {
        setCatalog(data);
        const first = data.producers[0];
        setProducerId(first.id);
        setWasteTypeId(first.default_waste_type_id);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  const selectedProducer = useMemo(
    () => catalog?.producers.find((producer) => producer.id === producerId),
    [catalog, producerId],
  );

  const handleProducerChange = (id: string) => {
    setProducerId(id);
    const producer = catalog?.producers.find((item) => item.id === id);
    if (producer) setWasteTypeId(producer.default_waste_type_id);
  };

  const submitDeclaration = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    setProposal(null);
    try {
      const created = await api.createDeclaration({
        producer_id: producerId,
        waste_type_id: wasteTypeId,
        quantity_kg: quantity,
        frequency,
        availability_date: availabilityDate,
        notes,
      });
      const compatible = await api.matches(created.id);
      setDeclaration(created);
      setMatches(compatible);
      setSelectedUnitId(compatible[0]?.processing_unit_id ?? "");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Erreur inattendue");
    } finally {
      setBusy(false);
    }
  };

  const generateProposal = async () => {
    if (!declaration || !selectedUnitId) return;
    setBusy(true);
    setError("");
    try {
      setProposal(await api.proposal(declaration.id, selectedUnitId));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Erreur inattendue");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main>
      <header className="hero">
        <nav className="nav-shell" aria-label="Navigation principale">
          <a className="brand" href="#top" aria-label="BioLoop CI — accueil">
            <span className="brand-mark">BL</span>
            <span>BioLoop <em>CI</em></span>
          </a>
          <a className="nav-link" href="#declaration">Lancer le parcours</a>
        </nav>
        <div className="hero-grid" id="top">
          <div>
            <span className="eyebrow">SIREXE Hackathon 2026 · tranches verticales 01 + 02</span>
            <h1>Du gisement déclaré au lot <span>traçable.</span></h1>
            <p className="hero-copy">
              Un parcours local pour déclarer un déchet organique, identifier une unité
              compatible, documenter une preuve, saisir une pesée et tracer la décision
              de l’unité — sans transformer une simulation en vérité scientifique.
            </p>
            <div className="hero-actions">
              <a className="primary-button" href="#declaration">Créer une déclaration</a>
              <span className="local-note"><i /> Démo locale · aucune API externe</span>
            </div>
          </div>
          <aside className="truth-card">
            <span className="truth-kicker">Règle de crédibilité</span>
            <p>Pas de coefficient validé, pas de prétention scientifique.</p>
            <ul>
              <li>Calcul déterministe et versionné</li>
              <li>Hypothèses et unités toujours visibles</li>
              <li>Validation humaine avant toute collecte</li>
            </ul>
            <EvidenceBadge level="P0" label="Simulation illustrative" />
          </aside>
        </div>
      </header>

      <section className="evidence-strip" aria-labelledby="evidence-title">
        <div className="section-shell">
          <div className="section-heading compact">
            <div>
              <span className="section-index">00</span>
              <h2 id="evidence-title">Lire le niveau de preuve</h2>
            </div>
            <p>Le statut voyage avec chaque donnée. Une déclaration P1 ne devient jamais une mesure P3.</p>
          </div>
          <div className="evidence-grid">
            {(catalog?.evidence_levels ?? [
              { proof_level: "P0", label: "Simulé", provenance: "simulated" },
              { proof_level: "P1", label: "Déclaré", provenance: "declared" },
              { proof_level: "P2", label: "Documenté", provenance: "documented" },
              { proof_level: "P3", label: "Mesuré", provenance: "measured" },
              { proof_level: "P4", label: "Vérifié", provenance: "verified" },
              { proof_level: "P5", label: "Certifié", provenance: "certified" },
            ]).map((item) => (
              <div className="evidence-definition" key={item.proof_level}>
                <EvidenceBadge level={item.proof_level} label={item.label} />
                <small>{evidenceDescriptions[item.proof_level]}</small>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="catalog-section section-shell" aria-labelledby="catalog-title">
        <div className="section-heading">
          <div>
            <span className="section-index">01</span>
            <h2 id="catalog-title">Le bassin de démonstration</h2>
          </div>
          <p>{catalog?.disclaimer ?? "Chargement du catalogue local…"}</p>
        </div>
        {catalog && (
          <>
            <div className="catalog-label">Producteurs fictifs · {catalog.producers.length}</div>
            <div className="producer-grid" data-testid="producer-list">
              {catalog.producers.map((producer) => (
                <article className="catalog-card producer-card" key={producer.id}>
                  <div className="card-heading">
                    <span className="producer-kind">{producer.kind}</span>
                    <EvidenceBadge level={producer.proof_level} />
                  </div>
                  <h3>{producer.name}</h3>
                  <p>{producer.locality}</p>
                </article>
              ))}
            </div>
            <div className="catalog-label units-label">Unités fictives · {catalog.processing_units.length}</div>
            <div className="units-grid" data-testid="unit-list">
              {catalog.processing_units.map((unit) => (
                <UnitCard unit={unit} catalog={catalog} key={unit.id} />
              ))}
            </div>
          </>
        )}
      </section>

      <section className="workflow-section" id="declaration" aria-labelledby="workflow-title">
        <div className="section-shell">
          <div className="section-heading light">
            <div>
              <span className="section-index">02</span>
              <h2 id="workflow-title">Déclarer, apparier, simuler</h2>
            </div>
            <p>Le calcul s'exécute côté API. Le navigateur ne contient aucune règle métier.</p>
          </div>

          <div className="workflow-grid">
            <form className="form-card" onSubmit={submitDeclaration}>
              <div className="step-title"><span>1</span><div><small>DONNÉE P1</small><h3>Déclarer un gisement</h3></div></div>
              <label>
                Producteur fictif
                <select value={producerId} onChange={(event) => handleProducerChange(event.target.value)} required>
                  {catalog?.producers.map((producer) => (
                    <option value={producer.id} key={producer.id}>{producer.name} — {producer.locality}</option>
                  ))}
                </select>
              </label>
              <div className="form-row">
                <label>
                  Type de déchet déclaré
                  <select value={wasteTypeId} onChange={(event) => setWasteTypeId(event.target.value)} required>
                    {catalog?.waste_types.map((waste) => (
                      <option value={waste.id} key={waste.id}>{waste.name}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Masse déclarée (kg)
                  <input data-testid="quantity-input" type="number" min="1" max="50000" step="0.01" value={quantity} onChange={(event) => setQuantity(event.target.value)} required />
                </label>
              </div>
              <div className="form-row">
                <label>
                  Fréquence
                  <select value={frequency} onChange={(event) => setFrequency(event.target.value)}>
                    <option value="ponctuelle">Ponctuelle</option>
                    <option value="quotidienne">Quotidienne</option>
                    <option value="hebdomadaire">Hebdomadaire</option>
                  </select>
                </label>
                <label>
                  Disponible à partir du
                  <input type="date" value={availabilityDate} onChange={(event) => setAvailabilityDate(event.target.value)} required />
                </label>
              </div>
              <label>
                Note facultative
                <textarea maxLength={280} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Ex. matières triées à confirmer sur place" />
              </label>
              <div className="form-proof">
                <EvidenceBadge level="P1" label="Quantité et type déclarés" />
                <EvidenceBadge level="P0" label={`Localisation fictive${selectedProducer ? ` · ${selectedProducer.locality}` : ""}`} />
              </div>
              <button className="primary-button full" type="submit" disabled={busy || !catalog}>
                {busy ? "Traitement…" : "Enregistrer et chercher une unité"}
              </button>
            </form>

            <div className={`match-card ${declaration ? "active" : ""}`}>
              <div className="step-title"><span>2</span><div><small>RÈGLES P0</small><h3>Choisir une unité compatible</h3></div></div>
              {!declaration ? (
                <div className="empty-state"><span>↳</span><p>La liste compatible apparaîtra après la déclaration.</p></div>
              ) : matches.length === 0 ? (
                <div className="empty-state warning"><span>!</span><p>Aucune unité fictive ne satisfait à la fois type et capacité. Modifiez la déclaration.</p></div>
              ) : (
                <>
                  <div className="declaration-recap" data-testid="declaration-recap">
                    <div><small>Déclaration</small><strong>{declaration.id}</strong></div>
                    <div><small>Masse</small><strong>{formatNumber(declaration.quantity_kg, 0)} kg <EvidenceBadge level="P1" /></strong></div>
                  </div>
                  <div className="match-options">
                    {matches.map((match) => (
                      <label className={`match-option ${selectedUnitId === match.processing_unit_id ? "selected" : ""}`} key={match.processing_unit_id}>
                        <input type="radio" name="unit" value={match.processing_unit_id} checked={selectedUnitId === match.processing_unit_id} onChange={() => setSelectedUnitId(match.processing_unit_id)} />
                        <span className="radio-mark" />
                        <span className="match-copy">
                          <strong>{match.processing_unit_name}</strong>
                          <small>{match.process}</small>
                          <span>{formatNumber(match.distance_straight_line_km, 2)} km à vol d'oiseau · {formatNumber(match.available_capacity_kg)} kg disponibles</span>
                        </span>
                        <EvidenceBadge level="P0" />
                      </label>
                    ))}
                  </div>
                  <p className="match-note">Compatibilité et capacité issues du catalogue fictif. Aucune analyse matière n'a été réalisée.</p>
                  <button data-testid="generate-proposal" className="primary-button full" type="button" onClick={generateProposal} disabled={busy || !selectedUnitId}>
                    {busy ? "Calcul…" : "Calculer les scénarios et la collecte"}
                  </button>
                </>
              )}
            </div>
          </div>
          {error && <div className="error-banner" role="alert">{error}</div>}
        </div>
      </section>

      {proposal && (
        <section className="results-section section-shell" data-testid="proposal-results" aria-labelledby="results-title">
          <div className="section-heading">
            <div>
              <span className="section-index">03</span>
              <h2 id="results-title">Une proposition auditable</h2>
            </div>
            <div className="result-ids"><span>{proposal.estimate.id}</span><span>{proposal.correlation_id}</span></div>
          </div>

          <div className="illustrative-alert">
            <EvidenceBadge level="P0" label="Simulation illustrative" />
            <div><strong>Ces résultats ne sont ni un rendement biogaz, ni une mesure.</strong><p>L'unité URI sert uniquement à démontrer le calcul, le versionnage et l'incertitude.</p></div>
          </div>

          <div className="scenario-grid">
            {proposal.estimate.scenarios.map((scenario) => (
              <article className={`scenario-card scenario-${scenario.key}`} key={scenario.key}>
                <span>SCÉNARIO {scenario.label.toUpperCase()}</span>
                <strong>{formatNumber(scenario.value, 2)}</strong>
                <p>{proposal.estimate.output_unit}</p>
                <small>{formatNumber(proposal.estimate.input_quantity_kg)} kg × {scenario.multiplier_uri_per_kg} URI/kg</small>
              </article>
            ))}
          </div>

          <div className="result-grid">
            <article className="audit-card">
              <div className="result-card-heading"><div><span className="card-number">A</span><h3>Hypothèses & source</h3></div><EvidenceBadge level="P0" /></div>
              <dl className="audit-list">
                <div><dt>Formule</dt><dd>{proposal.estimate.formula}</dd></div>
                <div><dt>Jeu de facteurs</dt><dd>{proposal.estimate.factor_set_id} · v{proposal.estimate.factor_set_version}</dd></div>
                <div><dt>Source</dt><dd>{proposal.estimate.source.title}<small>{proposal.estimate.source.reference}</small></dd></div>
                <div><dt>Empreinte</dt><dd><code>{proposal.estimate.calculation_hash}</code></dd></div>
              </dl>
              <p className="source-note">{proposal.estimate.source.note}</p>
              <ul className="assumption-list">
                {proposal.estimate.assumptions.map((assumption) => <li key={assumption}>{assumption}</li>)}
              </ul>
            </article>

            <article className="route-card">
              <div className="result-card-heading"><div><span className="card-number">B</span><h3>Collecte proposée</h3></div><EvidenceBadge level="P0" /></div>
              <div className="route-metric"><strong>{formatNumber(proposal.route.total_straight_line_km, 2)} km</strong><span>aller-retour géodésique illustratif</span></div>
              <div className="route-line">
                {proposal.route.stops.map((stop) => (
                  <div className="route-stop" key={`${stop.order}-${stop.role}`}>
                    <span>{stop.order}</span>
                    <div><strong>{stop.name}</strong><small>{stop.role} · {stop.window}</small></div>
                  </div>
                ))}
              </div>
              <p className="route-method">{proposal.route.method}</p>
              <div className="human-gate"><span>✓</span><p><strong>Validation humaine requise</strong>Cette proposition ne planifie ni ne déclenche une collecte réelle.</p></div>
            </article>
          </div>
        </section>
      )}

      {proposal && declaration && (
        <TraceabilityWorkflow declaration={declaration} proposal={proposal} />
      )}

      <footer>
        <div className="section-shell footer-shell">
          <div className="brand"><span className="brand-mark">BL</span><span>BioLoop <em>CI</em></span></div>
          <p>Démonstrateur local · données fictives · aucun paiement, crédit carbone, blockchain ou agent autonome.</p>
        </div>
      </footer>
    </main>
  );
}
