import type { CaseAlert, ClaimRow } from "../../api/types";
import type { GraphModel } from "../../components/network/graphModel";

/**
 * The entity the investigator is focusing on (picked in the network graph or
 * the linked-entity list). Claims, findings and brief citations filter to it.
 */
export interface EntityFocus {
  id: string;
  type: string;
  label: string;
}

export interface FocusMatches {
  /** The focused id plus providers it owns (owner focus reaches their claims). */
  entityIds: Set<string>;
  lineIds: Set<string>;
  alertIds: Set<string>;
  /** Brief/evidence citation ids that point at the focused entity's evidence. */
  citeIds: Set<string>;
}

function ownedProviders(model: GraphModel | undefined, ownerId: string): string[] {
  if (!model) return [];
  return model.edges
    .filter((edge) => edge.kind === "owns" && (edge.source === ownerId || edge.target === ownerId))
    .map((edge) => (edge.source === ownerId ? edge.target : edge.source));
}

export function rowTouches(row: ClaimRow, ids: Set<string>): boolean {
  return (
    ids.has(row.rendering_provider_id) ||
    (row.billing_provider_id !== null && ids.has(row.billing_provider_id)) ||
    (row.ordering_provider_id !== null && ids.has(row.ordering_provider_id)) ||
    (row.facility_id !== null && ids.has(row.facility_id)) ||
    ids.has(row.member.member_id)
  );
}

/** Works out which claim lines, alerts and citations belong to the focused entity. */
export function focusMatches(
  focus: EntityFocus,
  rows: ClaimRow[],
  alerts: CaseAlert[],
  model: GraphModel | undefined,
): FocusMatches {
  const entityIds = new Set([focus.id, ...(focus.type === "owner" ? ownedProviders(model, focus.id) : [])]);
  const lineIds = new Set(rows.filter((row) => rowTouches(row, entityIds)).map((row) => row.line_id));
  const alertIds = new Set(
    alerts
      .filter(
        (alert) =>
          entityIds.has(alert.entity_id) ||
          alert.evidence.owner_id === focus.id ||
          alert.line_ids.some((id) => lineIds.has(id)),
      )
      .map((alert) => alert.alert_id),
  );
  const citeIds = new Set([
    ...[...entityIds].map((id) => `provider:${id}`),
    ...[...lineIds].map((id) => `line:${id}`),
    ...[...alertIds].map((id) => `alert:${id}`),
  ]);
  return { entityIds, lineIds, alertIds, citeIds };
}
