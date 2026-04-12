import { NextResponse } from "next/server";

export async function POST(req: Request) {
  try {
    // 요청이 잘 들어오는지 확인
    const formData = await req.formData();
    console.log("업로드 요청 받음:", formData.get("title"));

    // 클라이언트가 기대하는 project_id 응답
    return NextResponse.json({ 
      project_id: 1, 
      title: formData.get("title") 
    });
  } catch (error) {
    return NextResponse.json({ error: "Server Error" }, { status: 500 });
  }
}