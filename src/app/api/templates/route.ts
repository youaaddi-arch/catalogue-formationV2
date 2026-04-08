import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function GET(request: NextRequest) {
  const category = request.nextUrl.searchParams.get("category");

  const templates = await prisma.template.findMany({
    where: category ? { category } : undefined,
    orderBy: { createdAt: "desc" },
  });

  return NextResponse.json(templates);
}

export async function POST(request: NextRequest) {
  const body = await request.json();

  if (!body.name || !body.htmlContent) {
    return NextResponse.json(
      { error: "Nom et contenu HTML requis" },
      { status: 400 }
    );
  }

  const template = await prisma.template.create({
    data: {
      name: body.name,
      category: body.category || "general",
      subject: body.subject || "",
      htmlContent: body.htmlContent,
    },
  });

  return NextResponse.json(template);
}

export async function PUT(request: NextRequest) {
  const body = await request.json();

  if (!body.id) {
    return NextResponse.json({ error: "ID requis" }, { status: 400 });
  }

  const template = await prisma.template.update({
    where: { id: body.id },
    data: {
      name: body.name,
      category: body.category,
      subject: body.subject,
      htmlContent: body.htmlContent,
    },
  });

  return NextResponse.json(template);
}

export async function DELETE(request: NextRequest) {
  const body = await request.json();

  if (!body.id) {
    return NextResponse.json({ error: "ID requis" }, { status: 400 });
  }

  await prisma.template.delete({ where: { id: body.id } });
  return NextResponse.json({ success: true });
}
