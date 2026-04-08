import nodemailer from "nodemailer";
import { prisma } from "./db";

export async function getTransporter() {
  const settings = await prisma.settings.findUnique({ where: { id: "default" } });

  if (!settings || !settings.smtpHost) {
    throw new Error("SMTP non configuré. Allez dans Paramètres pour configurer votre serveur SMTP.");
  }

  return nodemailer.createTransport({
    host: settings.smtpHost,
    port: settings.smtpPort,
    secure: settings.smtpPort === 465,
    auth: {
      user: settings.smtpUser,
      pass: settings.smtpPass,
    },
  });
}

export async function sendEmail({
  to,
  subject,
  html,
  text,
}: {
  to: string;
  subject: string;
  html: string;
  text?: string;
}) {
  const settings = await prisma.settings.findUnique({ where: { id: "default" } });
  const transporter = await getTransporter();

  const result = await transporter.sendMail({
    from: `"${settings?.fromName || "Email Marketing"}" <${settings?.fromEmail || "noreply@example.com"}>`,
    to,
    subject,
    html,
    text: text || html.replace(/<[^>]*>/g, ""),
  });

  return result;
}
