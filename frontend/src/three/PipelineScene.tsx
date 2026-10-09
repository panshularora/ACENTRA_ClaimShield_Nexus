import { Line, PerformanceMonitor } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { type MutableRefObject, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  AdditiveBlending,
  Color,
  type Group,
  type InstancedMesh,
  type Mesh,
  type MeshBasicMaterial,
  type MeshStandardMaterial,
  type PointLight,
} from "three";
import { MAX_PARTICLES, ParticleField } from "./particleField";

/** ClaimsWatch / HackForgeAI detector palette — black console, silver core. */
const SCENE = {
  bg: "#0a1016",
  surface: "#101820",
  core: "#c5d0c8",
  coreDim: "#3d4a52",
  line: "#c5d0c8",
  flagged: "#d46568",
  ring: "#5c6b72",
  rate: "#e6ebe4",
} as const;

const BASELINE_RING = 1.45;
const RATIO_MIN = 0.2;
const RATIO_MAX = 1.5;

const ease = (delta: number, rate: number) => 1 - Math.exp(-delta * rate);

const RING_POINTS = (() => {
  const points: [number, number, number][] = [];
  for (let i = 0; i <= 128; i++) {
    const a = (i / 128) * Math.PI * 2;
    points.push([Math.cos(a), Math.sin(a), 0]);
  }
  return points;
})();

function clampRatio(ratio: number): number {
  return Math.min(RATIO_MAX, Math.max(RATIO_MIN, ratio));
}

export interface LiveFlow {
  linesPerSecond: number;
  flaggedShare: number;
  rateRatio: number;
}

function flowFromProgress(p: number): LiveFlow {
  const t = Math.min(1, Math.max(0, p));
  return {
    linesPerSecond: 42 + t * 88,
    flaggedShare: 0.07 + t * 0.16,
    rateRatio: 0.42 + t * 0.78,
  };
}

function Particles({
  progressRef,
  reducedMotion,
}: {
  progressRef: MutableRefObject<number>;
  reducedMotion: boolean;
}) {
  const mesh = useRef<InstancedMesh>(null);
  const material = useRef<MeshBasicMaterial>(null);
  const [field] = useState(() => new ParticleField(SCENE.line, SCENE.flagged));
  const flow = useRef(1);
  const invalidate = useThree((state) => state.invalidate);

  useLayoutEffect(() => {
    if (mesh.current) field.attach(mesh.current);
  }, [field]);

  useEffect(() => {
    if (!reducedMotion || !mesh.current) return;
    const live = flowFromProgress(progressRef.current);
    field.seed(mesh.current, live.linesPerSecond, live.flaggedShare);
    if (material.current) material.current.opacity = 1;
    invalidate();
  }, [field, reducedMotion, progressRef, invalidate]);

  useFrame((_, delta) => {
    if (reducedMotion || !mesh.current) return;
    const dt = Math.min(delta, 0.1);
    const live = flowFromProgress(progressRef.current);
    flow.current += (1 - flow.current) * ease(dt, 2.5);
    field.step(mesh.current, dt, live.linesPerSecond, live.flaggedShare, flow.current);
  });

  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, MAX_PARTICLES]} frustumCulled={false}>
      <icosahedronGeometry args={[0.036, 1]} />
      <meshBasicMaterial ref={material} transparent opacity={1} toneMapped={false} />
    </instancedMesh>
  );
}

function Core({ progressRef, reducedMotion }: { progressRef: MutableRefObject<number>; reducedMotion: boolean }) {
  const body = useRef<Mesh>(null);
  const bodyMaterial = useRef<MeshStandardMaterial>(null);
  const shell = useRef<Group>(null);
  const shellMaterial = useRef<MeshBasicMaterial>(null);
  const light = useRef<PointLight>(null);
  const shock = useRef<Mesh>(null);
  const shockMaterial = useRef<MeshBasicMaterial>(null);
  const phase = useRef(0);
  const shockT = useRef(1);
  const fired = useRef(false);
  const target = useMemo(() => new Color(SCENE.core), []);
  const invalidate = useThree((state) => state.invalidate);

  useEffect(() => {
    if (!reducedMotion) return;
    const color = new Color(SCENE.core);
    bodyMaterial.current?.color.copy(color);
    bodyMaterial.current?.emissive.copy(color);
    if (bodyMaterial.current) bodyMaterial.current.emissiveIntensity = 0.35;
    shellMaterial.current?.color.copy(color);
    light.current?.color.copy(color);
    if (light.current) light.current.intensity = 5.5;
    invalidate();
  }, [reducedMotion, invalidate]);

  useFrame((_, delta) => {
    if (reducedMotion) return;
    const dt = Math.min(delta, 0.1);
    const live = flowFromProgress(progressRef.current);
    const above = live.rateRatio > 1;
    const coreHex = above ? SCENE.flagged : SCENE.core;
    const glow = above ? 0.85 : 0.35;
    const beat = above ? 3.2 : 1.4;
    const beatAmp = above ? 0.055 : 0.025;
    const spin = above ? 0.28 : 0.12;
    if (above && !fired.current) {
      shockT.current = 0;
      fired.current = true;
    }
    if (!above) fired.current = false;

    target.set(coreHex);
    const k = ease(dt, 3);
    const m = bodyMaterial.current;
    if (m) {
      m.color.lerp(target, k);
      m.emissive.lerp(target, k);
      m.emissiveIntensity += (glow - m.emissiveIntensity) * k;
    }
    shellMaterial.current?.color.lerp(target, k);
    if (light.current) {
      light.current.color.lerp(target, k);
      light.current.intensity += (2 + glow * 10 - light.current.intensity) * k;
    }
    phase.current += dt * beat;
    const pulse = Math.pow(Math.max(0, Math.sin(phase.current)), 6);
    body.current?.scale.setScalar(1 + beatAmp * (0.3 + pulse));
    if (shell.current) {
      shell.current.rotation.y += dt * spin;
      shell.current.rotation.x += dt * spin * 0.4;
    }
    if (shock.current && shockMaterial.current) {
      if (shockT.current < 1) {
        shockT.current = Math.min(1, shockT.current + dt / 1.6);
        const t = shockT.current;
        shock.current.visible = true;
        shock.current.scale.setScalar(0.7 + t * 3.2);
        shockMaterial.current.color.copy(target);
        shockMaterial.current.opacity = (1 - t) * 0.55;
      } else {
        shock.current.visible = false;
      }
    }
  });

  return (
    <group>
      <pointLight ref={light} position={[0, 0, 0]} intensity={4} distance={6} decay={1.6} />
      <mesh ref={body}>
        <icosahedronGeometry args={[0.55, 4]} />
        <meshStandardMaterial
          ref={bodyMaterial}
          color={SCENE.core}
          emissive={SCENE.core}
          emissiveIntensity={0.35}
          roughness={0.35}
          metalness={0.15}
        />
      </mesh>
      <group ref={shell}>
        <mesh>
          <icosahedronGeometry args={[0.82, 1]} />
          <meshBasicMaterial ref={shellMaterial} color={SCENE.core} wireframe transparent opacity={0.22} />
        </mesh>
      </group>
      <mesh ref={shock} visible={false}>
        <ringGeometry args={[0.96, 1, 96]} />
        <meshBasicMaterial
          ref={shockMaterial}
          transparent
          opacity={0}
          blending={AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

function Rings({ progressRef, reducedMotion }: { progressRef: MutableRefObject<number>; reducedMotion: boolean }) {
  const rate = useRef<Group>(null);
  const invalidate = useThree((state) => state.invalidate);

  useEffect(() => {
    if (!reducedMotion || !rate.current) return;
    const ratio = clampRatio(flowFromProgress(progressRef.current).rateRatio);
    rate.current.scale.setScalar(BASELINE_RING * ratio);
    invalidate();
  }, [reducedMotion, progressRef, invalidate]);

  useFrame((_, delta) => {
    if (reducedMotion || !rate.current) return;
    const live = flowFromProgress(progressRef.current);
    const ratio = clampRatio(live.rateRatio);
    const current = rate.current.scale.x;
    const next = current + (BASELINE_RING * ratio - current) * ease(Math.min(delta, 0.1), 2.5);
    rate.current.scale.setScalar(next);
  });

  return (
    <group>
      <group scale={BASELINE_RING}>
        <Line
          points={RING_POINTS}
          color={SCENE.ring}
          lineWidth={1.2}
          dashed
          dashSize={0.035}
          gapSize={0.03}
          transparent
          opacity={0.9}
        />
      </group>
      <group ref={rate} scale={BASELINE_RING * 0.55}>
        <Line points={RING_POINTS} color={SCENE.rate} lineWidth={1.6} transparent opacity={0.9} />
      </group>
    </group>
  );
}

function ContextWatcher({ onLost }: { onLost?: () => void }) {
  const gl = useThree((state) => state.gl);
  useEffect(() => {
    if (!onLost) return;
    const canvas = gl.domElement;
    const handle = (event: Event) => {
      event.preventDefault();
      onLost();
    };
    canvas.addEventListener("webglcontextlost", handle);
    return () => canvas.removeEventListener("webglcontextlost", handle);
  }, [gl, onLost]);
  return null;
}

/** Paid-claim lines falling into the rank core — same spherical detector as ClaimsWatch. */
export function PipelineScene({
  progressRef,
  reducedMotion = false,
  onContextLost,
}: {
  progressRef: MutableRefObject<number>;
  reducedMotion?: boolean;
  onContextLost?: () => void;
}) {
  const [maxDpr, setMaxDpr] = useState(1.75);
  const frameloop = reducedMotion ? "demand" : "always";

  return (
    <Canvas
      className="scene-canvas"
      frameloop={frameloop}
      dpr={[1, maxDpr]}
      camera={{ position: [0, 0.3, 8.2], fov: 36 }}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance", preserveDrawingBuffer: true }}
      aria-hidden="true"
    >
      <PerformanceMonitor onDecline={() => setMaxDpr(1)} />
      <ContextWatcher onLost={onContextLost} />
      <fog attach="fog" args={[SCENE.surface, 6.5, 12]} />
      <ambientLight intensity={0.35} />
      <directionalLight position={[3, 4, 5]} intensity={0.9} />
      <Rings progressRef={progressRef} reducedMotion={reducedMotion} />
      <Core progressRef={progressRef} reducedMotion={reducedMotion} />
      <Particles progressRef={progressRef} reducedMotion={reducedMotion} />
    </Canvas>
  );
}
