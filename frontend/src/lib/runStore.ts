const KEY = "claimshield.activeRun";

export interface StoredRun {
  runId: string;
  batchId: string;
  profile: string;
  seed: number;
  capacityHours: number;
  horizonDays: number;
}

export function readStoredRun(): StoredRun | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredRun;
    if (!parsed.runId) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function writeStoredRun(run: StoredRun): void {
  localStorage.setItem(KEY, JSON.stringify(run));
}
