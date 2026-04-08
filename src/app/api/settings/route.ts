import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import nodemailer from "nodemailer";

export async function GET() {
  let settings = await prisma.settings.findUnique({
    where: { id: "default" },
  });

  if (!settings) {
    settings = await prisma.settings.create({
      data: { id: "default" },
    });
  }

  // Don't send password to client
  return NextResponse.json({
    ...settings,
    smtpPass: settings.smtpPass ? "••••••••" : "",
  });
}

export async function PUT(request: NextRequest) {
  const body = await request.json();

  const data: Record<string, unknown> = {
    smtpHost: body.smtpHost || "",
    smtpPort: body.smtpPort || 587,
    smtpUser: body.smtpUser || "",
    fromEmail: body.fromEmail || "",
    fromName: body.fromName || "",
    company: body.company || "",
    website: body.website || "",
  };

  // Only update password if it's not the masked version
  if (body.smtpPass && body.smtpPass !== "••••••••") {
    data.smtpPass = body.smtpPass;
  }

  const settings = await prisma.settings.upsert({
    where: { id: "default" },
    update: data,
    create: { id: "default", ...data } as Record<string, unknown> & { id: string },
  });

  return NextResponse.json(settings);
}

export async function POST(request: NextRequest) {
  const body = await request.json();

  if (body.action === "test") {
    const settings = await prisma.settings.findUnique({
      where: { id: "default" },
    });

    if (!settings || !settings.smtpHost) {
      return NextResponse.json(
        { error: "SMTP non configuré" },
        { status: 400 }
      );
    }

    try {
      const transporter = nodemailer.createTransport({
        host: settings.smtpHost,
        port: settings.smtpPort,
        secure: settings.smtpPort === 465,
        auth: {
          user: settings.smtpUser,
          pass: settings.smtpPass,
        },
      });

      await transporter.verify();
      return NextResponse.json({ success: true });
    } catch (err) {
      return NextResponse.json(
        {
          error: `Connexion échouée: ${
            err instanceof Error ? err.message : "Erreur inconnue"
          }`,
        },
        { status: 500 }
      );
    }
  }

  return NextResponse.json({ error: "Action inconnue" }, { status: 400 });
}
