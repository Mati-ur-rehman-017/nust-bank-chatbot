import { useRef, useState } from "react";

interface UploadFormProps {
  onUpload: (file: File) => Promise<{ success: boolean; error?: string }>;
  isLoading: boolean;
}

export function UploadForm({ onUpload, isLoading }: UploadFormProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{
    type: "success" | "error" | null;
    message: string;
  }>({ type: null, message: "" });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const ALLOWED_EXTENSIONS = [".json", ".csv", ".xlsx", ".xls", ".txt", ".pdf"];
  const MAX_SIZE_MB = 10;

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const validateFile = (file: File): string | null => {
    const extension = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      return `Unsupported file type. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File too large. Maximum size: ${MAX_SIZE_MB}MB`;
    }
    return null;
  };

  const handleFile = async (file: File) => {
    setUploadStatus({ type: null, message: "" });

    const error = validateFile(file);
    if (error) {
      setUploadStatus({ type: "error", message: error });
      return;
    }

    const result = await onUpload(file);
    if (result.success) {
      setUploadStatus({
        type: "success",
        message: `Successfully uploaded ${file.name}`,
      });
      // Clear the input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      // Clear success message after 3 seconds
      setTimeout(
        () => setUploadStatus({ type: null, message: "" }),
        3000,
      );
    } else {
      setUploadStatus({
        type: "error",
        message: result.error || "Upload failed",
      });
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      await handleFile(files[0]);
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      await handleFile(files[0]);
    }
  };

  return (
    <div className="space-y-3">
      <div
        className={`relative cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
          isDragging
            ? "border-[#10a37f] bg-[#10a37f]/10"
            : "border-[#4e4f60] bg-[#40414f]"
        } ${isLoading ? "pointer-events-none opacity-60" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept={ALLOWED_EXTENSIONS.join(",")}
          onChange={handleFileSelect}
          disabled={isLoading}
        />

        {isLoading ? (
          <div className="flex flex-col items-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#4e4f60] border-t-[#10a37f]" />
            <p className="mt-3 text-sm font-medium text-[#c5c5d2]">
              Uploading and indexing...
            </p>
          </div>
        ) : (
          <>
            <p className="text-4xl">📁</p>
            <p className="mt-2 text-sm font-medium text-[#c5c5d2]">
              Drag & drop files here, or click to browse
            </p>
            <p className="mt-1 text-xs text-[#8e8ea0]">
              Supports JSON, CSV, XLSX, text, and PDF files (max {MAX_SIZE_MB}MB)
            </p>
          </>
        )}
      </div>

      {uploadStatus.type && (
        <div
          className={`rounded-lg p-3 text-sm ${
            uploadStatus.type === "success"
              ? "bg-[#10a37f]/20 text-[#10a37f]"
              : "bg-red-500/20 text-red-400"
          }`}
        >
          {uploadStatus.message}
        </div>
      )}
    </div>
  );
}
