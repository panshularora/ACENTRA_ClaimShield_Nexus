import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { type MutableRefObject, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { BufferAttribute, BufferGeometry, type Group, type LineBasicMaterial } from "three";
import { LineField } from "./lineField";

const FOG = "#0a1016";

export interface MotionRefs {
  scroll: MutableRefObject<number>;
  pointer: MutableRefObject<{ x: number; y: number }>;
  reveal: MutableRefObject<number>;
}

function Lattice({ motion, reducedMotion }: { motion: MotionRefs; reducedMotion: boolean }) {
  const field = useMemo(() => new LineField(), []);
  const geom = useRef<BufferGeometry>(null);
  const group = useRef<Group>(null);
  const material = useRef<LineBasicMaterial>(null);
  const time = useRef(0);
  const scrollSmoothed = useRef(0);
  const revealSmoothed = useRef(motion.reveal.current);
  const pointerSmoothed = useRef({ x: 0, y: 0 });
  const invalidate = useThree((state) => state.invalidate);

  useLayoutEffect(() => {
    const geometry = geom.current;
    if (!geometry) return;
    field.write(0, 0, 0, 0);
    geometry.setAttribute("position", new BufferAttribute(field.positions, 3));
    geometry.setAttribute("color", new BufferAttribute(field.colors, 3));
    geometry.computeBoundingSphere();
    invalidate();
  }, [field, invalidate]);

  useFrame((_, delta) => {
    const geometry = geom.current;
    if (!geometry) return;
    const dt = Math.min(delta, 0.08);
    const target = Math.min(1, Math.max(0, motion.scroll.current));
    const revealTarget = Math.min(1, Math.max(0, motion.reveal.current));
    scrollSmoothed.current += (target - scrollSmoothed.current) * (1 - Math.exp(-dt * 3.2));
    revealSmoothed.current += (revealTarget - revealSmoothed.current) * (1 - Math.exp(-dt * 4.2));
    pointerSmoothed.current.x += (motion.pointer.current.x - pointerSmoothed.current.x) * (1 - Math.exp(-dt * 2.4));
    pointerSmoothed.current.y += (motion.pointer.current.y - pointerSmoothed.current.y) * (1 - Math.exp(-dt * 2.4));
    if (!reducedMotion) time.current += dt;

    const p = scrollSmoothed.current;
    const shown = revealSmoothed.current;
    field.write(p, time.current, pointerSmoothed.current.x, pointerSmoothed.current.y);
    const pos = geometry.getAttribute("position");
    const col = geometry.getAttribute("color");
    pos.needsUpdate = true;
    col.needsUpdate = true;
    if (material.current) material.current.opacity = 0.55 * shown;

    if (group.current) {
      group.current.rotation.y = -0.18 + p * 0.55 + pointerSmoothed.current.x * 0.12;
      group.current.rotation.x = -0.42 - p * 0.22 + pointerSmoothed.current.y * 0.08;
      group.current.position.z = p * 1.8;
      group.current.position.y = -0.35 - p * 0.4;
      const s = 0.94 + 0.06 * shown;
      group.current.scale.setScalar(s);
    }
  });

  return (
    <group ref={group}>
      <lineSegments frustumCulled={false} visible>
        <bufferGeometry ref={geom} />
        <lineBasicMaterial
          ref={material}
          vertexColors
          transparent
          opacity={0.12}
          depthWrite={false}
          toneMapped={false}
        />
      </lineSegments>
    </group>
  );
}

function CameraRig({ motion }: { motion: MotionRefs }) {
  useFrame(({ camera }, delta) => {
    const dt = Math.min(delta, 0.08);
    const p = Math.min(1, Math.max(0, motion.scroll.current));
    const px = motion.pointer.current.x;
    const py = motion.pointer.current.y;
    const tx = px * 0.45;
    const ty = 1.15 + p * 0.85 - py * 0.25;
    const tz = 8.4 - p * 3.6;
    const k = 1 - Math.exp(-dt * 2.2);
    camera.position.x += (tx - camera.position.x) * k;
    camera.position.y += (ty - camera.position.y) * k;
    camera.position.z += (tz - camera.position.z) * k;
    camera.lookAt(0, 0.15, 0);
  });
  return null;
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

/** Full-viewport fine white lattice. Scroll pulls the camera through the sheet. */
export function LineFieldScene({
  motion,
  reducedMotion = false,
  onContextLost,
}: {
  motion: MotionRefs;
  reducedMotion?: boolean;
  onContextLost?: () => void;
}) {
  const [dpr, setDpr] = useState(1.5);

  return (
    <Canvas
      className="line-field-canvas"
      frameloop={reducedMotion ? "demand" : "always"}
      dpr={[1, dpr]}
      camera={{ position: [0, 1.15, 8.4], fov: 38, near: 0.1, far: 40 }}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      aria-hidden="true"
      onCreated={({ gl }) => {
        gl.setClearColor(0x000000, 0);
        if (window.devicePixelRatio > 1.75) setDpr(1.25);
      }}
    >
      <ContextWatcher onLost={onContextLost} />
      <fog attach="fog" args={[FOG, 7, 16]} />
      <CameraRig motion={motion} />
      <Lattice motion={motion} reducedMotion={reducedMotion} />
    </Canvas>
  );
}
