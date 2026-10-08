import { Canvas } from "@react-three/fiber";
import { Html, Line, OrbitControls } from "@react-three/drei";
import { useMemo, useState } from "react";
import { Color, Vector3 } from "three";
import type { NetworkEdge, NetworkNode, NetworkPack } from "../api/types";
import { palette } from "./palette";

const TYPE_COLOR: Record<string, string> = {
  provider: palette.green,
  member: palette.gold,
  facility: "#7ec8ff",
  owner: palette.harm,
};

function layout(nodes: NetworkNode[]): Record<string, Vector3> {
  const groups: Record<string, NetworkNode[]> = {};
  for (const n of nodes) {
    (groups[n.type] ??= []).push(n);
  }
  const pos: Record<string, Vector3> = {};
  const place = (list: NetworkNode[], radius: number, y: number) => {
    list.forEach((n, i) => {
      const a = (i / Math.max(1, list.length)) * Math.PI * 2 - Math.PI / 2;
      pos[n.id] = new Vector3(Math.cos(a) * radius, y, Math.sin(a) * radius);
    });
  };
  place(groups.provider ?? [], 2.15, 0.35);
  place(groups.owner ?? [], 1.15, 1.35);
  place(groups.facility ?? [], 3.05, 0.7);
  place(groups.member ?? [], 3.7, -0.15);
  for (const n of nodes) {
    if (!pos[n.id]) pos[n.id] = new Vector3((Math.random() - 0.5) * 2, 0.2, (Math.random() - 0.5) * 2);
  }
  return pos;
}

function NodeMesh({
  node,
  position,
  selected,
  onSelect,
}: {
  node: NetworkNode;
  position: Vector3;
  selected: boolean;
  onSelect: () => void;
}) {
  const color = TYPE_COLOR[node.type] ?? palette.paper;
  const r = node.primary ? 0.22 : node.type === "provider" ? 0.16 : 0.11;
  return (
    <group position={position}>
      <mesh
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
        onPointerOver={() => {
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          document.body.style.cursor = "";
        }}
      >
        <sphereGeometry args={[r, 20, 20]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={selected || node.primary ? 0.55 : 0.18}
          roughness={0.28}
        />
      </mesh>
      {(selected || node.primary) && (
        <Html center distanceFactor={8} position={[0, r + 0.22, 0]}>
          <div className="n3-tip">
            <strong>{node.label}</strong>
            <span>{node.type}</span>
          </div>
        </Html>
      )}
    </group>
  );
}

export function NetworkGraph({
  pack,
  enabled,
  onSelect,
  reduced,
}: {
  pack: NetworkPack;
  enabled: Record<string, boolean>;
  onSelect: (id: string, type: string) => void;
  reduced: boolean;
}) {
  const [picked, setPicked] = useState<string | null>(pack.primary_entity_id);
  const positions = useMemo(() => layout(pack.nodes), [pack.nodes]);
  const edges = useMemo(
    () => pack.edges.filter((e) => enabled[e.kind] !== false),
    [pack.edges, enabled],
  );

  return (
    <Canvas camera={{ position: [0, 3.4, 7.4], fov: 40 }} dpr={[1, 1.6]} gl={{ antialias: true, alpha: true }}>
      <color attach="background" args={[palette.navy]} />
      <fog attach="fog" args={[palette.navy, 9, 18]} />
      <ambientLight intensity={0.42} />
      <directionalLight position={[4, 6, 4]} intensity={1.05} />
      <pointLight position={[0, 2, 0]} color={palette.green} intensity={8} distance={10} />
      <gridHelper args={[14, 14, new Color("#0d7a38"), new Color("#12323c")]} />
      {edges.map((edge, i) => (
        <EdgeLine key={`${edge.source}-${edge.target}-${edge.kind}-${i}`} edge={edge} positions={positions} />
      ))}
      {pack.nodes.map((node) =>
        positions[node.id] ? (
          <NodeMesh
            key={node.id}
            node={node}
            position={positions[node.id]}
            selected={picked === node.id}
            onSelect={() => {
              setPicked(node.id);
              onSelect(node.id, node.type);
            }}
          />
        ) : null,
      )}
      <OrbitControls
        enablePan={!reduced}
        autoRotate={!reduced}
        autoRotateSpeed={0.55}
        maxPolarAngle={1.4}
        minDistance={4}
        maxDistance={12}
      />
    </Canvas>
  );
}

function EdgeLine({
  edge,
  positions,
}: {
  edge: NetworkEdge;
  positions: Record<string, Vector3>;
}) {
  const a = positions[edge.source];
  const b = positions[edge.target];
  if (!a || !b) return null;
  const color = edge.kind === "referral" || edge.kind === "owns" || edge.kind.includes("shared") ? palette.green : "#4d6b75";
  return (
    <Line
      points={[
        [a.x, a.y, a.z],
        [b.x, b.y, b.z],
      ]}
      color={color}
      lineWidth={1.2}
      transparent
      opacity={0.7}
    />
  );
}
