import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function GET(request: NextRequest) {
  const search = request.nextUrl.searchParams.get("search") || "";

  const contacts = await prisma.contact.findMany({
    where: search
      ? {
          OR: [
            { email: { contains: search } },
            { firstName: { contains: search } },
            { lastName: { contains: search } },
            { company: { contains: search } },
          ],
        }
      : undefined,
    orderBy: { createdAt: "desc" },
  });

  return NextResponse.json(contacts);
}

export async function POST(request: NextRequest) {
  const body = await request.json();

  if (!body.email) {
    return NextResponse.json({ error: "Email requis" }, { status: 400 });
  }

  // Format tags
  let tags = body.tags || "";
  if (typeof tags === "string" && !tags.startsWith("[")) {
    tags = JSON.stringify(
      tags
        .split(",")
        .map((t: string) => t.trim())
        .filter(Boolean)
    );
  }

  try {
    const contact = await prisma.contact.create({
      data: {
        email: body.email,
        firstName: body.firstName || "",
        lastName: body.lastName || "",
        company: body.company || "",
        phone: body.phone || "",
        tags,
      },
    });
    return NextResponse.json(contact);
  } catch {
    return NextResponse.json(
      { error: "Ce contact existe déjà" },
      { status: 409 }
    );
  }
}

export async function PUT(request: NextRequest) {
  const body = await request.json();

  if (!body.id) {
    return NextResponse.json({ error: "ID requis" }, { status: 400 });
  }

  let tags = body.tags || "";
  if (typeof tags === "string" && !tags.startsWith("[")) {
    tags = JSON.stringify(
      tags
        .split(",")
        .map((t: string) => t.trim())
        .filter(Boolean)
    );
  }

  const contact = await prisma.contact.update({
    where: { id: body.id },
    data: {
      email: body.email,
      firstName: body.firstName || "",
      lastName: body.lastName || "",
      company: body.company || "",
      phone: body.phone || "",
      tags,
      status: body.status,
    },
  });

  return NextResponse.json(contact);
}

export async function DELETE(request: NextRequest) {
  const body = await request.json();

  if (!body.id) {
    return NextResponse.json({ error: "ID requis" }, { status: 400 });
  }

  await prisma.contact.delete({ where: { id: body.id } });
  return NextResponse.json({ success: true });
}
