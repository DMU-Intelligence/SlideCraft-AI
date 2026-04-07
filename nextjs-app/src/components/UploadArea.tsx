"use client";

import { FileText, Upload } from "lucide-react";
import { useState, type DragEvent } from "react";

const ACCEPT =
  ".pdf,.docx,.txt,.md,.csv,.log,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown";

interface UploadAreaProps {
  onFileSelect: (file: File) => void;
  selectedFile: File | null;
}

export function UploadArea({ onFileSelect, selectedFile }: UploadAreaProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      onFileSelect(files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFileSelect(files[0]);
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`relative cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center transition-all duration-200 md:p-12 ${
        isDragging
          ? "border-blue-500 bg-blue-50"
          : "border-gray-200 hover:border-blue-300 hover:bg-gray-50"
      }`}
    >
      <input
        type="file"
        accept={ACCEPT}
        onChange={handleFileInput}
        className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
      />

      <div className="flex flex-col items-center gap-4">
        {selectedFile ? (
          <>
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-blue-100">
              <FileText className="h-8 w-8 text-blue-600" />
            </div>
            <div>
              <p className="font-medium text-gray-700">{selectedFile.name}</p>
              <p className="mt-1 text-sm text-gray-500">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
            <p className="text-sm text-blue-600">클릭하거나 드래그하여 변경</p>
          </>
        ) : (
          <>
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gray-100">
              <Upload className="h-8 w-8 text-gray-400" />
            </div>
            <div>
              <p className="font-medium text-gray-700">문서를 여기에 드래그하여 업로드하세요</p>
              <p className="mt-1 text-sm text-gray-500">PDF, DOCX, TXT 등 · 또는 클릭하여 선택</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
