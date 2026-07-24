// Simple, low-churn theming: each theme swaps the page background and an accent color via CSS
// variables. The white-alpha surfaces used throughout read well on any of these dark backgrounds.

export interface Theme {
  id: string;
  name: string;
  bg: string; // CSS background (color or gradient)
  accent: string; // hex accent
  swatch: string; // small preview color
}

export const THEMES: Theme[] = [
  { id: "midnight", name: "Midnight", bg: "radial-gradient(1200px 800px at 70% -10%, #16204a 0%, #0b1020 55%)", accent: "#38bdf8", swatch: "#0b1020" },
  { id: "slate", name: "Slate", bg: "radial-gradient(1200px 800px at 70% -10%, #273244 0%, #0f141b 55%)", accent: "#60a5fa", swatch: "#0f141b" },
  { id: "forest", name: "Forest", bg: "radial-gradient(1200px 800px at 70% -10%, #123528 0%, #081712 55%)", accent: "#34d399", swatch: "#081712" },
  { id: "plum", name: "Plum", bg: "radial-gradient(1200px 800px at 70% -10%, #35204a 0%, #140c1f 55%)", accent: "#c084fc", swatch: "#140c1f" },
  { id: "ember", name: "Ember", bg: "radial-gradient(1200px 800px at 70% -10%, #3a1f1a 0%, #1a0f0c 55%)", accent: "#fb923c", swatch: "#1a0f0c" },
  { id: "carbon", name: "Carbon", bg: "radial-gradient(1200px 800px at 70% -10%, #1c1c1f 0%, #0a0a0b 55%)", accent: "#a1a1aa", swatch: "#0a0a0b" },
];

const KEY = "usbip.theme";

export function applyTheme(id: string): void {
  const theme = THEMES.find((t) => t.id === id) ?? THEMES[0];
  const root = document.documentElement;
  root.style.setProperty("--bg", theme.bg);
  root.style.setProperty("--accent", theme.accent);
}

export function loadThemeId(): string {
  return localStorage.getItem(KEY) ?? THEMES[0].id;
}

export function saveTheme(id: string): void {
  localStorage.setItem(KEY, id);
  applyTheme(id);
}
