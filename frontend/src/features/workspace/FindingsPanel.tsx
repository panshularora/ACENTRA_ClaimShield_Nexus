import type { CaseAlert } from "../../api/types";
import { EmptyState } from "../../components/ui/States";
import { PeerCompare } from "./PeerCompare";
import { AlertLineageBlock } from "./ProvenancePanel";

const APPROACH: Record<string, { label: string; tone: string }> = {
  hard_rule: { label: "Hard rule", tone: "tone-danger" },
  rules: { label: "Hard rule", tone: "tone-danger" },
  behavioral_anomaly: { label: "Peer anomaly", tone: "tone-warning" },
  anomaly: { label: "Peer anomaly", tone: "tone-warning" },
  network_graph: { label: "Network graph", tone: "tone-info" },
  graph: { label: "Network graph", tone: "tone-info" },
};

interface Finding {
  alert: CaseAlert;
  /** Every alert id folded into this finding (same rule on several lines). */
  alertIds: string[];
  lineIds: string[];
}

function collapseAlerts(alerts: CaseAlert[]): Finding[] {
  const map = new Map<string, Finding>();
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
  /** Alert ids that belong to the focused network entity, or null for no focus. */
  focusAlertIds: Set<string> | null;
  focusLabel: string | null;
  onOpen: (alertId: string) => void;
}

/** Detector findings as cards; anomaly findings carry the provider-vs-peer chart. */
export function FindingsPanel({ alerts, focusAlertIds, focusLabel, onOpen }: FindingsPanelProps) {
  const all = collapseAlerts(alerts);
  const rows = focusAlertIds ? all.filter((f) => f.alertIds.some((id) => focusAlertIds.has(id))) : all;
  return (
    <section className="findings" aria-labelledby="findings-title">
      <div className="section-subhead">
        <h3 id="findings-title">Findings</h3>
        <span className="muted">
          {focusAlertIds ? `${rows.length} of ${all.length} involve ${focusLabel}` : `${all.length} signal${all.length === 1 ? "" : "s"}`}
        </span>
      </div>
      {rows.length === 0 ? (
        <EmptyState title={focusAlertIds ? "No findings involve this entity" : "No detector findings"} compact>
          {focusAlertIds ? "Clear the network selection to see every finding on the case." : null}
        </EmptyState>
      ) : (
        <ul className="finding-list">
          {rows.map(({ alert, lineIds }) => {
            const approach = APPROACH[alert.approach ?? alert.detector] ?? { label: alert.detector, tone: "" };
            return (
              <li key={alert.alert_id} className="finding">
                <div className="finding-head">
                  <span className={`badge ${approach.tone}`}>{approach.label}</span>
                  <span className="mono muted">{alert.rule_id ?? alert.detector}</span>
                  {alert.policy_ref ? <span className="muted">Policy {alert.policy_ref}</span> : null}
                </div>
                <h4>{alert.label ?? alert.rule_title ?? alert.rule_id}</h4>
                {alert.review_reason ? <p>{alert.review_reason}</p> : null}
                <p className="muted">
                  <span className="mono">{alert.entity_id}</span> · {lineIds.length} supporting claim line
                  {lineIds.length === 1 ? "" : "s"}
                </p>
                {alert.evidence?.peer_group ? <PeerCompare evidence={alert.evidence} /> : null}
                <div className="finding-actions">
                  <button type="button" className="btn small" onClick={() => onOpen(alert.alert_id)}>
                    Trace evidence
                  </button>
                  {alert.lineage ? (
                    <details>
                      <summary>Where this came from</summary>
                      <AlertLineageBlock lineage={alert.lineage} />
                    </details>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
