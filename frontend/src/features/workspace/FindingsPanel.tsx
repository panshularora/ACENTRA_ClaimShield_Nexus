import type { CaseAlert } from "../../api/types";
import { PeerCompare } from "./PeerCompare";

const APPROACH: Record<string, string> = {
  hard_rule: "Hard rule",
  behavioral_anomaly: "Behavioral anomaly",
  network_graph: "Network graph",
  rules: "Hard rule",
  anomaly: "Behavioral anomaly",
  graph: "Network graph",
};

function collapseAlerts(alerts: CaseAlert[]): CaseAlert[] {
  const map = new Map<string, CaseAlert>();
  for (const alert of alerts) {
    const key = alert.rule_id ?? alert.detector ?? alert.alert_id;
    const prev = map.get(key);
    if (!prev) {
      map.set(key, { ...alert, line_ids: [...alert.line_ids] });
      continue;
    }
    map.set(key, {
      ...prev,
      line_ids: [...new Set([...prev.line_ids, ...alert.line_ids])],
    });
  }
  return [...map.values()];
}

export function FindingsPanel({
  alerts,
  onOpen,
}: {
  alerts: CaseAlert[];
  onOpen: (alertId: string) => void;
}) {
  const rows = collapseAlerts(alerts);
  return (
    <div className="findings">
      <header className="ws-panel-head">
        <div>
          <p className="kicker">Why it was flagged</p>
          <h2>Findings</h2>
        </div>
        <span className="muted mono">{rows.length} signal{rows.length === 1 ? "" : "s"}</span>
      </header>
      <p className="muted">
        Each card is a suspicion to verify. Inspect the claims, fields, rule, or peer comparison
        before you record a disposition.
      </p>
      {rows.length === 0 ? (
        <p className="muted">No detector findings on this case.</p>
      ) : (
        <ul className="finding-list">
          {rows.map((alert) => {
            const approach = APPROACH[alert.approach ?? alert.detector] ?? alert.detector;
            return (
              <li key={alert.alert_id}>
                <button type="button" className="finding-card" onClick={() => onOpen(alert.alert_id)}>
                  <span className={`badge approach-${alert.approach ?? alert.detector}`}>{approach}</span>
                  <strong>{alert.label ?? alert.rule_title ?? alert.rule_id}</strong>
                  <span className="mono">{alert.rule_id ?? alert.detector}</span>
                  {alert.policy_ref && <span className="muted">Policy {alert.policy_ref}</span>}
                  <span className="muted">{alert.line_ids.length} supporting claim line(s)</span>
                  <p>{alert.review_reason}</p>
                </button>
                {alert.evidence?.peer_group ? <PeerCompare evidence={alert.evidence} /> : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
