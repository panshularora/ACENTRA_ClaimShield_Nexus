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

export function FindingsPanel({
  alerts,
  onOpen,
}: {
  alerts: CaseAlert[];
  onOpen: (alertId: string) => void;
}) {
  return (
    <div className="findings">
      <p className="kicker">Why it was flagged</p>
      <p className="muted">
        Each row is a suspicion to verify. Inspect the claims, fields, rule, or peer comparison
        before you record a disposition.
      </p>
      {alerts.length === 0 ? (
        <p className="muted">No detector findings on this case.</p>
      ) : (
        <ul className="finding-list">
          {alerts.map((alert) => {
            const approach = APPROACH[alert.approach ?? alert.detector] ?? alert.detector;
            return (
              <li key={alert.alert_id}>
                <button type="button" className="finding-card" onClick={() => onOpen(alert.alert_id)}>
                  <span className={`badge approach-${alert.approach ?? alert.detector}`}>{approach}</span>
                  <strong>{alert.label ?? alert.rule_title ?? alert.rule_id}</strong>
                  <span className="mono">{alert.rule_id ?? alert.detector}</span>
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
