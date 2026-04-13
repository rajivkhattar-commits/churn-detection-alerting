/** Persisted user choice; effective theme is resolved for `data-theme` on `<html>`. */

export type ThemePreference = "dark" | "light" | "system";

export const THEME_STORAGE_KEY = "churn-ui-theme-preference";

export function getStoredPreference(): ThemePreference {
  try {
    const v = localStorage.getItem(THEME_STORAGE_KEY);
    if (v === "dark" || v === "light" || v === "system") return v;
  } catch {
    /* ignore */
  }
  return "system";
}

export function effectiveTheme(pref: ThemePreference): "dark" | "light" {
  if (pref === "dark" || pref === "light") return pref;
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function applyDocumentTheme(effective: "dark" | "light"): void {
  document.documentElement.setAttribute("data-theme", effective);
  document.documentElement.style.colorScheme =
    effective === "dark" ? "dark" : "light";
}
