// src/app/api/export/pptx/route.ts
import { NextResponse } from "next/server";

// ❌ export default 사용 금지
// ✅ 반드시 export async function POST 라고 써야 합니다.
export async function POST(req: Request) {
  try {
    const body = await req.json();
    console.log("PPT 다운로드 요청 프로젝트 ID:", body.project_id);

    // 가짜 파일 데이터 생성
    const mockContent = "This is a mock PPTX file content";
    const buffer = Buffer.from(mockContent, "utf-8");

    return new NextResponse(buffer, {
      status: 200,
      headers: {
        "Content-Type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "Content-Disposition": `attachment; filename="presentation.pptx"`,
      },
    });
  } catch (error) {
    console.error("Download API Error:", error);
    return NextResponse.json({ error: "다운로드 서버 에러" }, { status: 500 });
  }
}