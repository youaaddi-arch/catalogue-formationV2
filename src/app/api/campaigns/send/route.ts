import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { sendEmail } from "@/lib/email";

export async function POST(request: NextRequest) {
  const body = await request.json();

  if (!body.campaignId) {
    return NextResponse.json(
      { error: "campaignId requis" },
      { status: 400 }
    );
  }

  const campaign = await prisma.campaign.findUnique({
    where: { id: body.campaignId },
    include: {
      recipients: {
        include: { contact: true },
      },
    },
  });

  if (!campaign) {
    return NextResponse.json(
      { error: "Campagne introuvable" },
      { status: 404 }
    );
  }

  if (campaign.recipients.length === 0) {
    return NextResponse.json(
      { error: "Aucun destinataire sélectionné" },
      { status: 400 }
    );
  }

  // Load settings for template variables
  const settings = await prisma.settings.findUnique({
    where: { id: "default" },
  });

  let totalSent = 0;
  let totalBounced = 0;

  // Update campaign status to sending
  await prisma.campaign.update({
    where: { id: campaign.id },
    data: { status: "sending" },
  });

  for (const recipient of campaign.recipients) {
    try {
      // Replace template variables
      let html = campaign.htmlContent;
      html = html.replace(/\{\{prenom\}\}/g, recipient.contact.firstName || "");
      html = html.replace(/\{\{nom\}\}/g, recipient.contact.lastName || "");
      html = html.replace(
        /\{\{entreprise\}\}/g,
        settings?.company || recipient.contact.company || ""
      );
      html = html.replace(/\{\{email\}\}/g, recipient.contact.email);

      let subject = campaign.subject;
      subject = subject.replace(
        /\{\{prenom\}\}/g,
        recipient.contact.firstName || ""
      );
      subject = subject.replace(
        /\{\{nom\}\}/g,
        recipient.contact.lastName || ""
      );
      subject = subject.replace(
        /\{\{entreprise\}\}/g,
        settings?.company || ""
      );

      await sendEmail({
        to: recipient.contact.email,
        subject,
        html,
      });

      await prisma.campaignRecipient.update({
        where: { id: recipient.id },
        data: { status: "sent", sentAt: new Date() },
      });

      totalSent++;
    } catch {
      await prisma.campaignRecipient.update({
        where: { id: recipient.id },
        data: { status: "failed" },
      });
      totalBounced++;
    }
  }

  // Update campaign stats
  const finalStatus = totalSent > 0 ? "sent" : "failed";
  await prisma.campaign.update({
    where: { id: campaign.id },
    data: {
      status: finalStatus,
      sentAt: new Date(),
      totalSent,
      totalBounced,
    },
  });

  return NextResponse.json({
    success: true,
    totalSent,
    totalBounced,
    status: finalStatus,
  });
}
