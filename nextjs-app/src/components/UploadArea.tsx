"use client";

import { FileText, Upload } from "lucide-react";
import { useState, type DragEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";

const ACCEPT = ".pdf,application/pdf";

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
    if (files.length > 0 && files[0].type === "application/pdf") {
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
      className={`relative cursor-pointer rounded-xl p-10 text-center transition-colors duration-200 md:p-14 ${
        isDragging
          ? "sketchy-border-active bg-accent/5"
          : "sketchy-border hover:bg-ink/[0.02]"
      }`}
    >
      <input
        type="file"
        accept={ACCEPT}
        onChange={handleFileInput}
        className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
        aria-label="PDF 파일 업로드"
      />

      <AnimatePresence mode="wait">
        {selectedFile ? (
          <motion.div
            key="selected"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex flex-col items-center gap-4"
          >
            <div className="flex h-14 w-14 items-center justify-center rounded-full border border-border-subtle">
              <FileText className="h-6 w-6 text-ink" strokeWidth={1.5} />
            </div>
            <div>
              <p className="font-medium tracking-tight text-ink">{selectedFile.name}</p>
              <p className="mt-1 text-sm text-ink-light">
                {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
            <p className="text-sm text-accent">클릭하거나 드래그하여 변경</p>
          </motion.div>
        ) : (
          <motion.div
            key="empty"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex flex-col items-center gap-4"
          >
            <div className="flex h-14 w-14 items-center justify-center rounded-full border border-border-subtle">
              <Upload className="h-6 w-6 text-ink-faint" strokeWidth={1.5} />
            </div>
            <div>
              <p className="font-medium tracking-tight text-ink">
                PDF를 여기에 드래그하여 업로드하세요
              </p>
              <p className="mt-1 text-sm text-ink-light">또는 클릭하여 파일 선택</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
