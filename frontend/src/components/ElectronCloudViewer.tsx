"use client";

import { useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Points, PointMaterial } from "@react-three/drei";
import * as THREE from "three";

export type CloudPoint = {
  x: number;
  y: number;
  z: number;
  probability: number;
};

const DEEP_BLUE = new THREE.Color("#050e24");
const MID_CYAN = new THREE.Color("#22d3ee");
const PEAK_WHITE = new THREE.Color("#f0fdfa");

function probabilityToColor(t: number): THREE.Color {
  const clamped = Math.min(1, Math.max(0, t));
  let c: THREE.Color;
  if (clamped < 0.5) {
    c = DEEP_BLUE.clone().lerp(MID_CYAN, clamped * 2);
  } else {
    c = MID_CYAN.clone().lerp(PEAK_WHITE, (clamped - 0.5) * 2);
  }
  // Emphasize low-density regions as fainter (approximates per-point opacity on PointsMaterial).
  const fade = 0.38 + 0.62 * clamped;
  return c.multiplyScalar(fade);
}

/** Fallback Schrödinger-style cloud when API omits `cloud_data` (H₂-scale coordinates, Å). */
export function mockH2ElectronCloud(resolution = 14): CloudPoint[] {
  const extent = 1.35;
  const rL = new THREE.Vector3(-0.3705, 0, 0);
  const rR = new THREE.Vector3(0.3705, 0, 0);
  const sigma = 0.34;
  const xs = Array.from(
    { length: resolution },
    (_, i) => -extent + (2 * extent * i) / (resolution - 1)
  );
  const raw: CloudPoint[] = [];
  for (const x of xs) {
    for (const y of xs) {
      for (const z of xs) {
        const p = new THREE.Vector3(x, y, z);
        const g = (c: THREE.Vector3) =>
          Math.exp(-p.clone().sub(c).lengthSq() / (2 * sigma * sigma));
        const bond = (g(rL) + g(rR)) / Math.SQRT2;
        const anti = (g(rL) - g(rR)) / Math.SQRT2;
        const prob = bond * bond * 0.65 + anti * anti * 0.15;
        raw.push({ x, y, z, probability: prob });
      }
    }
  }
  const maxP = Math.max(...raw.map((o) => o.probability), 1e-12);
  return raw.map((o) => ({
    ...o,
    probability: o.probability / maxP,
  }));
}

type ElectronCloudViewerProps = {
  cloudData: CloudPoint[];
  /** Nuclear positions in the same units as cloudData (Å). Defaults to H₂ along x. */
  nuclei?: [number, number, number][];
};

function NucleusDots({
  positions,
}: {
  positions: [number, number, number][];
}) {
  return (
    <group>
      {positions.map((pos, i) => (
        <mesh key={i} position={pos}>
          <sphereGeometry args={[0.045, 20, 20]} />
          <meshStandardMaterial
            color="#0f172a"
            emissive="#38bdf8"
            emissiveIntensity={2.2}
            metalness={0.2}
            roughness={0.35}
          />
        </mesh>
      ))}
    </group>
  );
}

function CloudScene({
  cloudData,
  nuclei,
}: {
  cloudData: CloudPoint[];
  nuclei: [number, number, number][];
}) {
  const { positions, colors } = useMemo(() => {
    const n = cloudData.length;
    const pos = new Float32Array(n * 3);
    const col = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const { x, y, z, probability } = cloudData[i];
      pos[i * 3] = x;
      pos[i * 3 + 1] = y;
      pos[i * 3 + 2] = z;
      const c = probabilityToColor(probability);
      col[i * 3] = c.r;
      col[i * 3 + 1] = c.g;
      col[i * 3 + 2] = c.b;
    }
    return { positions: pos, colors: col };
  }, [cloudData]);

  const pointSize = useMemo(() => {
    let e = 1.2;
    for (const p of cloudData) {
      e = Math.max(e, Math.abs(p.x), Math.abs(p.y), Math.abs(p.z));
    }
    return Math.max(0.014, Math.min(0.048, e * 0.022));
  }, [cloudData]);

  return (
    <>
      <color attach="background" args={["#09090b"]} />
      <fog attach="fog" args={["#09090b", 2.4, 9]} />

      <ambientLight intensity={0.22} color="#94a3b8" />
      <directionalLight
        position={[4, 5, 3]}
        intensity={0.85}
        color="#f1f5f9"
      />

      <Points positions={positions} colors={colors}>
        <PointMaterial
          vertexColors
          transparent
          opacity={0.9}
          size={pointSize}
          sizeAttenuation
          depthWrite={false}
        />
      </Points>

      <NucleusDots positions={nuclei} />

      <OrbitControls
        enablePan={false}
        enableZoom
        minDistance={0.85}
        maxDistance={8}
        enableDamping
        dampingFactor={0.08}
        rotateSpeed={0.82}
        target={[0, 0, 0]}
      />
    </>
  );
}

const DEFAULT_H2_NUCLEI: [number, number, number][] = [
  [-0.3705, 0, 0],
  [0.3705, 0, 0],
];

export default function ElectronCloudViewer({
  cloudData,
  nuclei = DEFAULT_H2_NUCLEI,
}: ElectronCloudViewerProps) {
  const data = cloudData.length > 0 ? cloudData : mockH2ElectronCloud();

  return (
    <div className="relative w-full h-full min-h-[192px] rounded-md overflow-hidden border border-zinc-800/80 bg-zinc-950">
      <Canvas
        camera={{ position: [1.5, 1.1, 2.4], fov: 42, near: 0.02, far: 120 }}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: "high-performance",
        }}
        dpr={[1, 2]}
        className="touch-none select-none"
      >
        <CloudScene cloudData={data} nuclei={nuclei} />
      </Canvas>
      <div className="pointer-events-none absolute bottom-2 right-2 text-[9px] font-medium uppercase tracking-[0.14em] text-zinc-600">
        ψ*ψ · Schrödinger density
      </div>
    </div>
  );
}
