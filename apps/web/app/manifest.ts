import type { MetadataRoute } from "next";


export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "BioLoop CI — pilote local",
    short_name: "BioLoop CI",
    description: "Déclarations organiques et coordination pilote, avec niveaux de preuve explicites.",
    start_url: "/",
    display: "standalone",
    background_color: "#f5f2e9",
    theme_color: "#123d2d",
    lang: "fr",
    categories: ["business", "productivity"],
    icons: [
      { src: "/icon-192.svg", sizes: "192x192", type: "image/svg+xml", purpose: "any" },
      { src: "/icon-512.svg", sizes: "512x512", type: "image/svg+xml", purpose: "maskable" },
    ],
  };
}
