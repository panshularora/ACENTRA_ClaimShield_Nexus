import type { ClaimRow, TimelineEvent } from "../../api/types";
import { isoDateMs, weekStartMs } from "../../lib/format";

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

export interface WeekBucket {
  week: number;
  subjectPaid: number;
  linkedPaid: number;
  lines: number;
  referrals: number;
  stays: number;
}

export interface TimelineMarker {
  week: number;
  label: string;
}

/** Weekly paid amounts and line counts from claim rows, with gaps filled with zero weeks. */
export function weeklyBuckets(rows: ClaimRow[], events: TimelineEvent[], subjectId: string): WeekBucket[] {
  const byWeek = new Map<number, WeekBucket>();
  const bucket = (ms: number): WeekBucket => {
    const week = weekStartMs(ms);
    let hit = byWeek.get(week);
    if (!hit) {
      hit = { week, subjectPaid: 0, linkedPaid: 0, lines: 0, referrals: 0, stays: 0 };
      byWeek.set(week, hit);
    }
    return hit;
  };
  for (const row of rows) {
    const ms = isoDateMs(row.dos_from);
    if (ms === null) continue;
    const b = bucket(ms);
    b.lines += 1;
    if (row.rendering_provider_id === subjectId || row.billing_provider_id === subjectId) b.subjectPaid += row.paid;
    else b.linkedPaid += row.paid;
  }
  for (const event of events) {
    const ms = isoDateMs(event.ts);
    if (ms === null) continue;
    if (event.kind === "referral") bucket(ms).referrals += 1;
    else if (event.kind === "facility") bucket(ms).stays += 1;
  }
  if (byWeek.size === 0) return [];
  const weeks = [...byWeek.keys()].sort((a, b) => a - b);
  const out: WeekBucket[] = [];
  for (let w = weeks[0]; w <= weeks[weeks.length - 1]; w += WEEK_MS) {
    out.push(byWeek.get(w) ?? { week: w, subjectPaid: 0, linkedPaid: 0, lines: 0, referrals: 0, stays: 0 });
  }
  return out;
}

/** Prior-investigation open/close events become vertical markers on the time axis. */
export function investigationMarkers(events: TimelineEvent[]): TimelineMarker[] {
  return events
    .filter((event) => event.kind === "investigation")
    .flatMap((event) => {
      const ms = isoDateMs(event.ts);
      return ms === null ? [] : [{ week: weekStartMs(ms), label: event.title }];
    });
}
