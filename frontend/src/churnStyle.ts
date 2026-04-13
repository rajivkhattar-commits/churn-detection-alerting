/** Keys match backend `churn_type_probs` (baseline model). */
export type ChurnStyleKey = "soft" | "hard" | "operational";

export const CHURN_STYLE_SHORT: Record<ChurnStyleKey, string> = {
  soft: "Soft — demand & pricing",
  hard: "Hard — strategic exit",
  operational: "Operational — ops & setup",
};

export const CHURN_STYLE_SALES: Record<ChurnStyleKey, { lead: string; detail: string }> = {
  soft: {
    lead: "Mostly looks like demand and commercial pressure",
    detail:
      "Often reversible: competition, margin, menu, or relationship. Benchmark against similar venues and test commercial levers before assuming a permanent breakup.",
  },
  hard: {
    lead: "Mostly looks like a strategic or contractual exit",
    detail:
      "Suggests a durable leave decision, not just a bad week. Align with ENT on contract, who else won the account, and exec stakeholders — not only support tickets.",
  },
  operational: {
    lead: "Mostly looks like operations, hours, or configuration",
    detail:
      "Often fixable: closures, hours gaps, sync issues, or program pauses. Pair with support and confirm setup before treating it as pure commercial churn intent.",
  },
};

export function parseChurnStyleKey(k: string): ChurnStyleKey | null {
  const x = k.toLowerCase();
  if (x === "soft" || x === "hard" || x === "operational") return x;
  return null;
}

export function churnStyleSorted(
  probs: Record<string, unknown> | undefined
): { key: ChurnStyleKey; p: number }[] {
  if (!probs) return [];
  const out: { key: ChurnStyleKey; p: number }[] = [];
  for (const [k, v] of Object.entries(probs)) {
    const key = parseChurnStyleKey(k);
    if (key == null) continue;
    const p = Number(v);
    if (!Number.isFinite(p)) continue;
    out.push({ key, p });
  }
  return out.sort((a, b) => b.p - a.p);
}
