import type { CaseAlert } from "../../api/types";
import { EmptyState } from "../../components/ui/States";
import { findingCopy } from "../../lib/plainLanguage";
import { APPROACH_PLAIN, EvidenceStory, storyFromAlert, whereSummary } from "./EvidenceStory";
import { PeerCompare } from "./PeerCompare";

function collapseAlerts(alerts: CaseAlert[]): { alert: CaseAlert; alertIds: string[]; lineIds: string[] }[] {
  const map = new Map<string, { alert: CaseAlert; alertIds: string[]; lineIds: string[] }>();
  for (const alert of alerts) {
    const key = alert.rule_id ?? alert.detector ?? alert.alert_id;
    const prev = map.get(key);
    if (!prev) {
      map.set(key, { alert, alertIds: [alert.alert_id], lineIds: [...alert.line_ids] });
    } else {
      prev.alertIds.push(alert.alert_id);
      prev.lineIds = [...new Set([...prev.lineIds, ...alert.line_ids])];
    }
  }
  return [...map.values()];
}

interface FindingsPanelProps {
  alerts: CaseAlert[];
  focusAlertIds: Set<string> | null;
  focusLabel: string | null;
  onOpen: (alertId: string) => void;
}

/** Open packets: problem, where, and why are on the page. Cite lines in the drawer. */
export function FindingsPanel({ alerts, focusAlertIds, focusLabel, onOpen }: FindingsPanelProps) {
  const all = collapseAlerts(alerts);
  const rows = focusAlertIds ? all.filter((f) => f.alertIds.some((id) => focusAlertIds.has(id))) : all;
  return (
    <section className="findings" aria-labelledby="findings-title">
      <div className="section-subhead">
        <h3 id="findings-title">What we noticed</h3>
        <span className="muted">
          {focusAlertIds
            ? `${rows.length} of ${all.length} involve ${focusLabel}`
            : `${all.length} pattern${all.length === 1 ? "" : "s"} to review`}
        </span>
      </div>
      {rows.length === 0 ? (
        <EmptyState title={focusAlertIds ? "Nothing here involves this party" : "No patterns on this case"} compact>
          {focusAlertIds ? "Clear the network selection to see every pattern on this case." : null}
        </EmptyState>
      ) : (
        <div className="findings-scroll">
          <ul className="finding-list">
            {rows.map(({ alert, lineIds }) => {
              const approachKey = alert.approach ?? alert.detector ?? "";
              const approach = APPROACH_PLAIN[approachKey] ?? { label: "Paid-claim check", tech: "" };
              const story = storyFromAlert({ ...alert, line_ids: lineIds });
              const copy = findingCopy(story.kind, story.fallbackTitle);
              const where = whereSummary(alert.evidence, lineIds);
              return (
                <li key={alert.alert_id} className="finding is-open">
                  <div className="finding-head">
                    <span className={`badge ${toneFor(approachKey)}`}>{approach.label}</span>
                    {where ? <span className="finding-where">{where}</span> : null}
                  </div>
                  <h4>{copy.title}</h4>
                  <EvidenceStory
                    {...story}
                    peer={alert.evidence?.peer_group ? <PeerCompare evidence={alert.evidence} /> : null}
                  />
                  <div className="finding-actions">
                    <button type="button" className="btn small ghost" onClick={() => onOpen(alert.alert_id)}>
                      Cited claim lines
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
}

function toneFor(approach: string): string {
  if (approach === "hard_rule" || approach === "rules") return "tone-danger";
  if (approach === "behavioral_anomaly" || approach === "anomaly") return "tone-warning";
  if (approach === "network_graph" || approach === "graph") return "tone-info";
  return "";
}
