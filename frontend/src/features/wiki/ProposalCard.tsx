import { Link } from "@tanstack/react-router";
import type { WikiProposal } from "../../api/types";
import { humanize } from "../../lib/format";
import "./wiki.css";

/** A precedent proposal drafted from a human decision; compact mode links to the full page. */
export function ProposalCard({
  proposal,
  compact = false,
}: {
  proposal: WikiProposal;
  compact?: boolean;
}) {
  const body = proposal.body ?? {};
  const rules = body.rules ?? [];
  const evidence = body.key_evidence ?? [];
  const sources = body.sources ?? [];
  const changes = body.changes ?? [];
  const pattern = body.observed_pattern ?? body.confirmed_pattern ?? [];

  return (
    <article className={`panel proposal-card status-${proposal.status}`}>
      {proposal.banner && (
        <p className="banner warn" role="status">
          {proposal.banner}
        </p>
      )}
      <header>
        <p className="kicker">
          {humanize(proposal.kind)} · {humanize(proposal.status)}
        </p>
        <h3>{proposal.title}</h3>
        <p className="mono muted">
          {proposal.proposal_id}
          {proposal.page_id ? ` · ${proposal.page_id}` : ""}
        </p>
      </header>
      <dl className="facts dense">
        <div>
          <dt>Source case</dt>
          <dd className="mono">{body.source_case ?? proposal.source_case_id}</dd>
        </div>
        <div>
          <dt>Decision / outcome</dt>
          <dd>
            {body.decision ?? "—"} / {body.outcome ?? "—"}
          </dd>
        </div>
        <div>
          <dt>Pattern</dt>
          <dd>
            {pattern.length ? pattern.join(", ") : "Not recorded"}
            {body.pattern_status ? ` (${body.pattern_status})` : ""}
          </dd>
        </div>
        {body.decision_context ? (
          <div>
            <dt>Decision context</dt>
            <dd>{body.decision_context}</dd>
          </div>
        ) : null}
      </dl>
      {!compact && (
        <>
          <section>
            <h4>Relevant rules</h4>
            {rules.length === 0 ? (
              <p className="muted">No stored rule ids on this proposal.</p>
            ) : (
              <ul className="compact-list">
                {rules.map((rule) => (
                  <li key={rule.rule_id}>
                    <span className="mono">{rule.rule_id}</span> {rule.title}
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section>
            <h4>Key evidence</h4>
            {evidence.length === 0 ? (
              <p className="muted">No stored detector evidence attached.</p>
            ) : (
              <ul className="compact-list">
                {evidence.map((item) => (
                  <li key={item.alert_id}>
                    {item.label} · {item.rule_id ?? "detector"} · {item.line_count} lines
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section>
            <h4>Supporting claims / lines</h4>
            <p className="mono muted">
              {(body.supporting_line_ids ?? []).slice(0, 12).join(" · ") || "None stored"}
            </p>
          </section>
          <section>
            <h4>Rationale</h4>
            <p>{body.rationale || "—"}</p>
          </section>
          <section>
            <h4>Limitations</h4>
            <ul className="compact-list">
              {(body.limitations ?? []).map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </section>
          <section>
            <h4>Changes</h4>
            <ul className="compact-list">
              {changes.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </section>
          <section>
            <h4>Sources</h4>
            <ul className="compact-list">
              {sources.map((src) => (
                <li key={`${src.kind}:${src.id}`}>
                  <span className="mono">
                    {src.kind}:{src.id}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
      {compact && (
        <p>
          <Link to="/wiki/proposals/$proposalId" params={{ proposalId: proposal.proposal_id }}>
            Open proposal
          </Link>
        </p>
      )}
    </article>
  );
}
