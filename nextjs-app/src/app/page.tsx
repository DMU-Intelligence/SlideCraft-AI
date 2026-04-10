"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";

import { GeneratedResults } from "@/components/GeneratedResults";
import { UploadArea } from "@/components/UploadArea";

const MOCK_SLIDES = [
  { id: 1, title: "Introduction to AI in Business" },
  { id: 2, title: "Key Benefits & ROI Analysis" },
  { id: 3, title: "Implementation Strategy" },
  { id: 4, title: "Case Studies & Success Stories" },
  { id: 5, title: "Future Trends & Roadmap" },
  { id: 6, title: "Q&A and Next Steps" },
];

export default function Home() {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [presentationTitle, setPresentationTitle] = useState("");
  const [isGenerated, setIsGenerated] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const script = `Welcome everyone to today's presentation on ${presentationTitle || "AI-Powered Solutions"}.

Slide 1: Introduction
Let's begin by exploring how artificial intelligence is revolutionizing the business landscape. In this presentation, we'll dive deep into the transformative power of AI and its practical applications across industries.

Slide 2: Key Benefits & ROI Analysis
The implementation of AI solutions has shown remarkable results. Companies adopting AI technologies have reported up to 40% improvement in operational efficiency and a 35% reduction in costs. We'll examine real data and metrics that demonstrate the tangible return on investment.

Slide 3: Implementation Strategy
Successful AI adoption requires a structured approach. We recommend a phased implementation that starts with identifying key pain points, followed by pilot programs, and then scaling across the organization. This minimizes risk while maximizing learning opportunities.

Slide 4: Case Studies & Success Stories
Let me share some inspiring examples. Company A increased their customer satisfaction by 50% through AI-powered chatbots. Company B reduced their processing time from days to hours using machine learning algorithms. These success stories demonstrate what's possible.

Slide 5: Future Trends & Roadmap
Looking ahead, we're seeing exciting developments in generative AI, autonomous systems, and predictive analytics. The roadmap for the next 3-5 years shows exponential growth in AI capabilities and accessibility.

Slide 6: Q&A and Next Steps
Now I'd like to open the floor for questions. Following this presentation, we'll provide you with detailed documentation and a personalized action plan to begin your AI journey.

Thank you for your attention. Let's build the future together.`;

  const handleGenerate = async () => {
    if (!uploadedFile || !presentationTitle || isGenerating) return;
    setIsGenerating(true);
    await new Promise((resolve) => setTimeout(resolve, 2000));
    setIsGenerating(false);
    setIsGenerated(true);
  };

  if (isGenerated) {
    return (
      <GeneratedResults
        slides={MOCK_SLIDES}
        script={script}
        presentationTitle={presentationTitle}
        onBack={() => setIsGenerated(false)}
      />
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50 p-6">
      <div className="w-full max-w-2xl">
        <header className="mb-12 text-center">
          <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 shadow-lg">
            <Sparkles className="h-8 w-8 text-white" />
          </div>
          <h1 className="mb-3 text-4xl font-bold text-gray-900">SlideCraft AI</h1>
          <p className="text-lg text-gray-600">문서를 업로드하면 발표 자료가 자동으로 생성됩니다.</p>
        </header>

        <section className="space-y-8 rounded-3xl border border-gray-100 bg-white p-10 shadow-xl">
          <div>
            <label className="mb-3 block text-sm font-semibold text-gray-700">PDF 문서 업로드</label>
            <UploadArea onFileSelect={setUploadedFile} selectedFile={uploadedFile} />
          </div>

          <div>
            <label htmlFor="title" className="mb-3 block text-sm font-semibold text-gray-700">
              발표 제목
            </label>
            <input
              id="title"
              type="text"
              value={presentationTitle}
              onChange={(e) => setPresentationTitle(e.target.value)}
              placeholder="발표 제목을 입력하세요..."
              className="w-full rounded-xl border border-gray-200 px-5 py-4 text-gray-900 outline-none transition-all placeholder:text-gray-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />
          </div>

          <button
            type="button"
            onClick={handleGenerate}
            disabled={!uploadedFile || !presentationTitle || isGenerating}
            className="flex w-full items-center justify-center gap-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4 text-lg font-semibold text-white shadow-lg transition-all duration-200 hover:from-blue-700 hover:to-indigo-700 hover:shadow-xl disabled:cursor-not-allowed disabled:from-gray-300 disabled:to-gray-300 disabled:shadow-none"
          >
            {isGenerating ? (
              <>
                <span className="h-5 w-5 animate-spin rounded-full border-[3px] border-white/30 border-t-white" />
                생성 중...
              </>
            ) : (
              <>
                <Sparkles className="h-5 w-5" />
                AI로 PPT 생성하기
              </>
            )}
          </button>

          <p className="text-center text-sm text-gray-500">AI가 문서를 분석하여 몇 초 안에 멋진 발표 자료를 만들어 드립니다</p>
        </section>

        <footer className="mt-8 text-center text-sm text-gray-500">고급 AI 기술로 제공됩니다</footer>
      </div>
    </main>
  );
}
