// src/app/api/generate/all/route.ts
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  // 테스트용 가짜 데이터
  return NextResponse.json({
    project_id: 1,
    title: "AI로 만든 결과물",
    slides: [
      { title: "첫 번째 슬라이드: 도입" },
      { title: "두 번째 슬라이드: 본론" },
      { title: "세 번째 슬라이드: 결론" }
    ],
    notes: "이것은 AI가 생성한 발표 대본입니다."
  });
}