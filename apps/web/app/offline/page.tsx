export default function OfflinePage() {
  return (
    <main className="offline-shell">
      <span className="brand-mark">BL</span>
      <h1>Connexion indisponible</h1>
      <p>
        Le shell BioLoop reste accessible. Seules les nouvelles déclarations peuvent être
        mises en attente ; comptes, preuves, mesures et portails privés exigent le réseau.
      </p>
      <a className="primary-button" href="/">Réessayer</a>
    </main>
  );
}
