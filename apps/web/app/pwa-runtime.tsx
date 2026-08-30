"use client";

import { useCallback, useEffect, useState } from "react";
import {
  listQueuedDeclarations,
  syncQueuedDeclarations,
  type OfflineDeclaration,
} from "@/lib/offline-declarations";


interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export function PwaRuntime() {
  const [online, setOnline] = useState(true);
  const [installPrompt, setInstallPrompt] = useState<InstallPromptEvent | null>(null);
  const [queue, setQueue] = useState<OfflineDeclaration[]>([]);

  const refreshQueue = useCallback(() => {
    if (!("indexedDB" in window)) return;
    listQueuedDeclarations().then(setQueue).catch(() => setQueue([]));
  }, []);

  useEffect(() => {
    setOnline(navigator.onLine);
    refreshQueue();
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" });
    }
    const onOnline = () => {
      setOnline(true);
      syncQueuedDeclarations().finally(refreshQueue);
    };
    const onOffline = () => setOnline(false);
    const onInstall = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as InstallPromptEvent);
    };
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    window.addEventListener("beforeinstallprompt", onInstall);
    window.addEventListener("bioloop-offline-queue-change", refreshQueue);
    if (navigator.onLine) syncQueuedDeclarations().finally(refreshQueue);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
      window.removeEventListener("beforeinstallprompt", onInstall);
      window.removeEventListener("bioloop-offline-queue-change", refreshQueue);
    };
  }, [refreshQueue]);

  const pending = queue.filter((item) => item.status !== "synced").length;
  return (
    <aside className="pwa-status" aria-live="polite" data-testid="pwa-status">
      <span className={online ? "online" : "offline"}>
        {online ? "En ligne" : "Hors connexion"}
      </span>
      {pending > 0 && <span>{pending} déclaration(s) à synchroniser</span>}
      {installPrompt && (
        <button
          type="button"
          onClick={async () => {
            await installPrompt.prompt();
            await installPrompt.userChoice;
            setInstallPrompt(null);
          }}
        >
          Installer l’application
        </button>
      )}
    </aside>
  );
}
