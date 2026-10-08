import { Canvas, useFrame } from "@react-three/fiber";
import { Float, Line } from "@react-three/drei";
import { useMemo, useRef } from "react";
import {
  Color,
  InstancedMesh,
  MathUtils,
  Object3D,
  Vector3,
  type Group,
  type Mesh,
} from "three";
import { palette } from "./palette";

const dummy = new Object3D();
const look = new Vector3();
const camGoal = new Vector3();

function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = Math.min(1, Math.max(0, (x - edge0) / (edge1 - edge0)));
  return t * t * (3 - 2 * t);
}

function ClaimCloud({
  progress,
  reduced,
}: {
  progress: number;
  reduced: boolean;
}) {
  const mesh = useRef<InstancedMesh>(null);
  const count = 220;
  const seeds = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => ({
        a: (i / count) * Math.PI * 2,
        r: 3.4 + (i % 9) * 0.42,
        y: ((i * 17) % 11) * 0.12 - 0.6,
        s: 0.7 + (i % 5) * 0.12,
        spin: 0.04 + (i % 7) * 0.01,
      })),
    [],
  );

  useFrame((state) => {
    const ref = mesh.current;
    if (!ref) return;
    const t = reduced ? 0 : state.clock.elapsedTime;
    const scatter = 1 - smoothstep(0.12, 0.38, progress);
    const cluster = smoothstep(0.28, 0.55, progress);
    for (let i = 0; i < count; i++) {
      const s = seeds[i];
      const a = s.a + t * s.spin;
      const x = Math.cos(a) * s.r * (0.85 + scatter * 0.35);
      const z = Math.sin(a) * s.r * 0.62;
      const y = s.y + Math.sin(t * 0.6 + i) * 0.12 * (reduced ? 0 : 1);
      dummy.position.set(
        MathUtils.lerp(x, Math.cos(s.a) * 1.6, cluster),
        MathUtils.lerp(y, 0.15 + (i % 5) * 0.08, cluster),
        MathUtils.lerp(z, Math.sin(s.a) * 1.6, cluster),
      );
      dummy.scale.setScalar(s.s * (0.55 + scatter * 0.5));
      dummy.rotation.set(0.4, a, 0.2);
      dummy.updateMatrix();
      ref.setMatrixAt(i, dummy.matrix);
    }
    ref.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, count]}>
      <boxGeometry args={[0.11, 0.025, 0.16]} />
      <meshStandardMaterial
        color={palette.mint}
        emissive={palette.green}
        emissiveIntensity={0.28}
        roughness={0.35}
        metalness={0.15}
      />
    </instancedMesh>
  );
}

function AlertSparks({ progress, reduced }: { progress: number; reduced: boolean }) {
  const group = useRef<Group>(null);
  const n = 18;
  const pts = useMemo(
    () =>
      Array.from({ length: n }, (_, i) => {
        const a = (i / n) * Math.PI * 2;
        return new Vector3(Math.cos(a) * 4.8, 0.2 + (i % 3) * 0.35, Math.sin(a) * 3.1);
      }),
    [],
  );
  useFrame((state) => {
    if (!group.current) return;
    const vis = smoothstep(0.08, 0.22, progress) * (1 - smoothstep(0.48, 0.62, progress));
    group.current.visible = vis > 0.02;
    const pulse = reduced ? 1 : 1 + Math.sin(state.clock.elapsedTime * 3) * 0.08;
    group.current.scale.setScalar(0.85 + vis * 0.3 * pulse);
  });
  return (
    <group ref={group}>
      {pts.map((p, i) => (
        <mesh key={i} position={p}>
          <octahedronGeometry args={[0.09, 0]} />
          <meshStandardMaterial
            color={i % 5 === 0 ? palette.harm : palette.alert}
            emissive={i % 5 === 0 ? palette.harm : palette.alert}
            emissiveIntensity={0.8}
          />
        </mesh>
      ))}
    </group>
  );
}

function IdentityRing({ progress, reduced }: { progress: number; reduced: boolean }) {
  const group = useRef<Group>(null);
  const nodes = useMemo(() => {
    const n = 7;
    return Array.from({ length: n }, (_, i) => {
      const a = (i / n) * Math.PI * 2;
      return { x: Math.cos(a) * 2.15, z: Math.sin(a) * 2.15, a, primary: i === 0 };
    });
  }, []);
  const lines = useMemo(() => {
    const pairs: [number, number][] = [
      [0, 1],
      [0, 2],
      [1, 3],
      [2, 4],
      [3, 5],
      [4, 6],
      [5, 6],
      [1, 4],
    ];
    return pairs.map(([a, b]) => [
      [nodes[a].x, 0.35, nodes[a].z] as [number, number, number],
      [nodes[b].x, 0.35, nodes[b].z] as [number, number, number],
    ]);
  }, [nodes]);

  useFrame((state) => {
    if (!group.current) return;
    const vis = smoothstep(0.32, 0.5, progress);
    group.current.visible = vis > 0.02;
    group.current.scale.setScalar(0.2 + vis * 0.95);
    group.current.rotation.y = reduced ? 0.4 : state.clock.elapsedTime * 0.12;
  });

  return (
    <group ref={group} position={[0, 0.1, 0]}>
      {lines.map((pts, i) => (
        <Line key={i} points={pts} color={palette.green} lineWidth={1.4} transparent opacity={0.7} />
      ))}
      {nodes.map((n, i) => (
        <mesh key={i} position={[n.x, 0.38, n.z]}>
          <sphereGeometry args={[n.primary ? 0.22 : 0.14, 24, 24]} />
          <meshStandardMaterial
            color={n.primary ? palette.green : palette.paper}
            emissive={n.primary ? palette.greenDeep : palette.mute}
            emissiveIntensity={n.primary ? 0.55 : 0.15}
            roughness={0.25}
          />
        </mesh>
      ))}
    </group>
  );
}

function QueueTowers({ progress }: { progress: number }) {
  const group = useRef<Group>(null);
  const lanes = [
    { h: 2.4, color: palette.harm, x: -1.8 },
    { h: 1.6, color: palette.green, x: -0.35 },
    { h: 0.9, color: palette.gold, x: 1.05 },
    { h: 0.45, color: palette.mute, x: 2.2 },
  ];
  useFrame(() => {
    if (!group.current) return;
    const vis = smoothstep(0.55, 0.72, progress);
    group.current.visible = vis > 0.02;
    group.current.position.y = MathUtils.lerp(-2.2, 0.05, vis);
  });
  return (
    <group ref={group}>
      {lanes.map((lane, i) => (
        <mesh key={i} position={[lane.x, lane.h / 2, 0.2]}>
          <boxGeometry args={[0.85, lane.h, 0.85]} />
          <meshStandardMaterial
            color={lane.color}
            emissive={lane.color}
            emissiveIntensity={0.22}
            transparent
            opacity={0.88}
            roughness={0.3}
          />
        </mesh>
      ))}
    </group>
  );
}

function ShieldMark({ progress, reduced }: { progress: number; reduced: boolean }) {
  const mesh = useRef<Mesh>(null);
  useFrame((state) => {
    if (!mesh.current) return;
    const vis = smoothstep(0.78, 0.92, progress);
    mesh.current.visible = vis > 0.02;
    mesh.current.scale.setScalar(0.4 + vis * 1.1);
    mesh.current.rotation.y = reduced ? 0.2 : state.clock.elapsedTime * 0.25;
  });
  return (
    <Float speed={reduced ? 0 : 1.4} rotationIntensity={0.2} floatIntensity={0.25}>
      <mesh ref={mesh} position={[0, 1.15, 0]} rotation={[0.4, 0.2, 0]}>
        <icosahedronGeometry args={[1.05, 1]} />
        <meshStandardMaterial
          color={palette.green}
          emissive={palette.greenDeep}
          emissiveIntensity={0.45}
          wireframe
          transparent
          opacity={0.85}
        />
      </mesh>
    </Float>
  );
}

function FloorGrid() {
  return (
    <gridHelper args={[28, 28, new Color(palette.greenDeep), new Color("#12323c")]} position={[0, -0.02, 0]} />
  );
}

function CameraRig({ progress, reduced }: { progress: number; reduced: boolean }) {
  useFrame((state) => {
    const p = progress;
    const x = MathUtils.lerp(0.15, 5.4, smoothstep(0, 1, p));
    const y = MathUtils.lerp(3.4, 1.55, smoothstep(0, 0.7, p));
    const z = MathUtils.lerp(9.6, 5.1, smoothstep(0, 1, p));
    camGoal.set(x, y, z);
    if (reduced) {
      state.camera.position.copy(camGoal);
    } else {
      state.camera.position.lerp(camGoal, 0.065);
    }
    look.set(0, 0.55, 0);
    state.camera.lookAt(look);
  });
  return null;
}

export function StoryScene({
  progress,
  reduced,
}: {
  progress: number;
  reduced: boolean;
}) {
  return (
    <Canvas
      camera={{ position: [0.15, 3.4, 9.6], fov: 42, near: 0.1, far: 80 }}
      dpr={[1, 1.75]}
      gl={{ antialias: true, alpha: true }}
      style={{ position: "absolute", inset: 0 }}
    >
      <color attach="background" args={[palette.navy]} />
      <fog attach="fog" args={[palette.navy, 12, 28]} />
      <ambientLight intensity={0.35} />
      <directionalLight position={[6, 8, 4]} intensity={1.15} color="#e8fff0" />
      <pointLight position={[-4, 3, -2]} intensity={18} color={palette.green} distance={16} />
      <pointLight position={[4, 2, 3]} intensity={10} color="#7ec8ff" distance={14} />
      <CameraRig progress={progress} reduced={reduced} />
      <FloorGrid />
      <ClaimCloud progress={progress} reduced={reduced} />
      <AlertSparks progress={progress} reduced={reduced} />
      <IdentityRing progress={progress} reduced={reduced} />
      <QueueTowers progress={progress} />
      <ShieldMark progress={progress} reduced={reduced} />
    </Canvas>
  );
}
