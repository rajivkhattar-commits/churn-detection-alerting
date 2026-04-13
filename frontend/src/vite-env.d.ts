/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** When `"true"`, build hides dev-only controls (slider, dry-run, etc.). Omit or `false` for full UI. */
  readonly VITE_STRICT_PROD?: string;
}
