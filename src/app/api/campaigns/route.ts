import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function GET(request: NextRequest) {
  const id = request.nextUrl.searchParams.get("id");
  const status = request.nextUrl.searchParams.get("status");
  const search = request.nextUrl.searchParams.get("search") || "";

  if (id) {
    const campaign = await prisma.campaign.findUnique({
      where: { id },
      include: {
        recipients: {
          include: { contact: true },
        },
      },
    });
    return NextResponse.json(campaign);
  }

  const where: Record<string, unknown> = {};
  if (status && status !== "all") {
    where.status = status;
  }
  if (search) {
    where.OR = [
      { name: { contains: search } },
      { subject: { contains: search } },
    ];
  }

  const campaigns = await prisma.campaign.findMany({
    where,
    orderBy: { createdAt: "desc" },
    include: {
      _count: { select: { recipients: true } },
    },
  });

  return NextResponse.json(campaigns);
}

export async function POST(request: NextRequest) {
  const body = await request.json();

  const campaign = await prisma.campaign.create({
    data: {
      name: body.name,
      subject: body.subject,
      htmlContent: body.htmlContent || "",
      textContent: body.textContent || "",
      status: body.status || "draft",
    },
  });

  // Add recipients if provided
  if (body.recipientIds && body.recipientIds.length > 0) {
    for (const contactId of body.recipientIds) {
      await prisma.campaignRecipient.upsert({
        where: { campaignId_contactId: { campaignId: campaign.id, contactId } },
        update: {},
        create: { campaignId: campaign.id, contactId },
      });
    }
  }

  return NextResponse.json(campaign);
}

export async function PUT(request: NextRequest) {
  const body = await request.json();

  if (!body.id) {
    return NextResponse.json({ error: "ID requis" }, { status: 400 });
  }

  const campaign = await prisma.campaign.update({
    where: { id: body.id },
    data: {
      name: body.name,
      subject: body.subject,
      htmlContent: body.htmlContent,
      textContent: body.textContent,
      status: body.status,
    },
  });

  // Update recipients if provided
  if (body.recipientIds) {
    // Remove existing recipients
    await prisma.campaignRecipient.deleteMany({
      where: { campaignId: campaign.id },
    });

    // Add new recipients
    for (const contactId of body.recipientIds) {
      await prisma.campaignRecipient.upsert({
        where: { campaignId_contactId: { campaignId: campaign.id, contactId } },
        update: {},
        create: { campaignId: campaign.id, contactId },
      });
    }
  }

  return NextResponse.json(campaign);
}

export async function DELETE(request: NextRequest) {
  const body = await request.json();

  if (!body.id) {
    return NextResponse.json({ error: "ID requis" }, { status: 400 });
  }

  await prisma.campaign.delete({ where: { id: body.id } });
  return NextResponse.json({ success: true });
}
