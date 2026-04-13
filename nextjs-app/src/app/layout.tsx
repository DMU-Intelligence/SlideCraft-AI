import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SlideCraft AI",
  description: "문서를 업로드하면 발표 자료가 자동으로 생성됩니다.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="ko"
      className={`${geistSans.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-paper font-[var(--font-geist-sans)] tracking-tight">
        {children}
      </body>
    </html>
  );
}
