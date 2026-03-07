export function UploadForm() {
  return (
    <div className="relative rounded-xl border-2 border-dashed border-[#4e4f60] bg-[#40414f] p-8 text-center">
      <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-[#343541]/90 backdrop-blur-sm">
        <div className="text-center">
          <p className="text-lg font-semibold text-[#c5c5d2]">Coming Soon</p>
          <p className="mt-1 text-sm text-[#8e8ea0]">
            Document upload will be available in a future update.
          </p>
        </div>
      </div>

      <div className="pointer-events-none opacity-40">
        <p className="text-4xl">📁</p>
        <p className="mt-2 text-sm font-medium text-[#c5c5d2]">
          Drag & drop files here, or click to browse
        </p>
        <p className="mt-1 text-xs text-[#8e8ea0]">
          Supports JSON, CSV, XLSX, and text files
        </p>
      </div>
    </div>
  );
}
