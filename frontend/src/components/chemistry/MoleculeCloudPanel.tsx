"use client";

import dynamic from "next/dynamic";
import type { CloudPoint } from "@/components/ElectronCloudViewer";
import { mockH2ElectronCloud } from "@/components/ElectronCloudViewer";

const ElectronCloudViewer = dynamic(
  () => import("@/components/ElectronCloudViewer"),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[300px] items-center justify-center rounded-md border border-gray-200 bg-gray-50">
        <span className="text-sm text-gray-500">Loading 3D viewer…</span>
      </div>
    ),
  }
);

export default function MoleculeCloudPanel({
  cloudData,
  nuclei,
  moleculeLabel,
  loading,
}: {
  cloudData?: CloudPoint[];
  nuclei: [number, number, number][];
  moleculeLabel: string;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="flex h-[300px] items-center justify-center rounded-md border border-gray-200 bg-gray-50">
        <span className="text-sm text-gray-500">Computing molecular state…</span>
      </div>
    );
  }

  const data =
    cloudData && cloudData.length > 0 ? cloudData : mockH2ElectronCloud(12);

  return (
    <div className="h-[300px] w-full overflow-hidden rounded-md border border-gray-200 bg-gray-100">
      <ElectronCloudViewer cloudData={data} nuclei={nuclei} />
      <p className="sr-only">Visualization for {moleculeLabel}</p>
    </div>
  );
}
