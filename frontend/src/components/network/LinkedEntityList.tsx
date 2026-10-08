import { money } from "../../lib/format";
import { edgeMeta, nodeMeta, type LinkedEntity } from "./networkModel";

function relationText(entity: LinkedEntity): string {
  const kinds = [...new Set(entity.relations.map((r) => edgeMeta(r.kind).label))];
  return kinds.join(" · ") || "No visible links";
}

const GROUPS: { title: string; test: (hop: number | null) => boolean }[] = [
  { title: "Direct links", test: (hop) => hop === 1 },
  { title: "Two hops", test: (hop) => hop === 2 },
  { title: "Further out", test: (hop) => hop === null || hop > 2 },
];

interface LinkedEntityListProps {
  entities: LinkedEntity[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

/** Keyboard-accessible alternative to the canvas: every linked entity as a button, grouped by hop. */
export function LinkedEntityList({ entities, selectedId, onSelect }: LinkedEntityListProps) {
  const linked = entities.filter((e) => e.hop !== 0 && e.node.type !== "member");
  const members = entities.filter((e) => e.node.type === "member").length;
  return (
    <nav className="linked-list" aria-label="Linked entities">
      {GROUPS.map((group) => {
        const rows = linked.filter((e) => group.test(e.hop));
        if (rows.length === 0) return null;
        return (
          <section key={group.title}>
            <h3>
              {group.title} <span className="muted">{rows.length}</span>
            </h3>
            <ul>
              {rows.map((entity) => (
                <li key={entity.node.id}>
                  <button
                    type="button"
                    aria-pressed={selectedId === entity.node.id}
                    onClick={() => onSelect(entity.node.id)}
                  >
                    <span className="linked-name">
                      {entity.node.label}
                      {entity.node.inCase ? <span className="badge">In case</span> : null}
                    </span>
                    <span className="linked-meta">
                      {nodeMeta(entity.node.type).label} · {relationText(entity)}
                      {entity.node.flaggedPaid ? ` · ${money(entity.node.flaggedPaid)} flagged` : ""}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
      {members > 0 ? (
        <p className="muted linked-foot">
          {members} member node{members === 1 ? "" : "s"} link providers through shared claims; select one in the graph to
          inspect it.
        </p>
      ) : null}
    </nav>
  );
}
