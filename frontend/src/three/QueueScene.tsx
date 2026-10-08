import { Canvas, useFrame } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
import { useMemo, useRef } from "react";
import { Color, MathUtils, type Mesh } from "three";
import type { Lane } from "../api/types";
import { palette } from "./palette";

const LANE_META: { lane: Lane; label: string; color: string; x: number }[] = [
  { lane: "harm_priority", label: "Harm", color: palette.harm, x: -2.4 },
  { lane: "selected", label: "Selected", color: palette.green, x: -0.8 },
  { lane: "needs_evidence", label: "Evidence", color: palette.gold, x: 0.8 },
  { lane: "overflow", label: "Monitor", color: palette.mute, x: 2.4 },
];

function Tower({
  hours,
  maxHours,
  color,
  x,
  label,
  active,
  onSelect,
  reduced,
}: {
  hours: number;
  maxHours: number;
  color: string;
  x: number;
  label: string;
  active: boolean;
  onSelect: () => void;
  reduced: boolean;
}) {
  const mesh = useRef<Mesh>(null);
  const target = Math.max(0.18, (hours / Math.max(1, maxHours)) * 2.8);
  useFrame(() => {
    if (!mesh.current) return;
    const h = MathUtils.lerp(mesh.current.scale.y, target, reduced ? 1 : 0.08);
    mesh.current.scale.y = h;
    mesh.current.position.y = h / 2;
  });
  return (
    <group position={[x, 0, 0]}>
      <mesh
        ref={mesh}
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
        <boxGeometry args={[1.1, 1, 1.1]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={active ? 0.45 : 0.18}
          transparent
          opacity={active ? 0.95 : 0.72}
          roughness={0.32}
        />
      </mesh>
      <Html position={[0, 3.15, 0]} center distanceFactor={10}>
        <div className={`q3-label ${active ? "on" : ""}`}>
          <strong>{label}</strong>
          <span>{hours.toFixed(1)}h</span>
        </div>
      </Html>
    </group>
  );
}

function Rig({ reduced }: { reduced: boolean }) {
  useFrame((state) => {
    if (reduced) return;
    const t = state.clock.elapsedTime;
    state.camera.position.x = Math.sin(t * 0.12) * 0.35;
    state.camera.lookAt(0, 1.1, 0);
  });
  return null;
}

export function QueueScene({
  hoursByLane,
  selected,
  onSelect,
  reduced,
}: {
  hoursByLane: Record<Lane, number>;
  selected: Lane | "all";
  onSelect: (lane: Lane) => void;
  reduced: boolean;
}) {
  const maxHours = useMemo(
    () => Math.max(4, ...LANE_META.map((l) => hoursByLane[l.lane] ?? 0)),
    [hoursByLane],
  );
  return (
    <Canvas camera={{ position: [0, 3.2, 7.2], fov: 38 }} dpr={[1, 1.6]} gl={{ antialias: true, alpha: true }}>
      <color attach="background" args={[palette.navy]} />
      <fog attach="fog" args={[palette.navy, 8, 18]} />
      <ambientLight intensity={0.4} />
      <directionalLight position={[4, 6, 3]} intensity={1.1} />
      <pointLight position={[-3, 2, 2]} color={palette.green} intensity={10} distance={12} />
      <gridHelper args={[12, 12, new Color("#0d7a38"), new Color("#12323c")]} />
      <Rig reduced={reduced} />
      {LANE_META.map((lane) => (
        <Tower
          key={lane.lane}
          hours={hoursByLane[lane.lane] ?? 0}
          maxHours={maxHours}
          color={lane.color}
          x={lane.x}
          label={lane.label}
          active={selected === "all" || selected === lane.lane}
          onSelect={() => onSelect(lane.lane)}
          reduced={reduced}
        />
      ))}
      {!reduced && <OrbitControls enablePan={false} maxPolarAngle={1.35} minDistance={5} maxDistance={11} />}
    </Canvas>
  );
}
