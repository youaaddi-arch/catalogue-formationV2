import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  // Create default settings
  await prisma.settings.upsert({
    where: { id: "default" },
    update: {},
    create: {
      id: "default",
      smtpHost: "",
      smtpPort: 587,
      smtpUser: "",
      smtpPass: "",
      fromEmail: "",
      fromName: "Mon Entreprise",
      company: "Mon Entreprise",
      website: "",
    },
  });

  // Create sample contacts
  const contacts = [
    { email: "jean.dupont@example.com", firstName: "Jean", lastName: "Dupont", company: "TechCorp", tags: '["prospect","formation"]' },
    { email: "marie.martin@example.com", firstName: "Marie", lastName: "Martin", company: "InnoSoft", tags: '["client","vip"]' },
    { email: "pierre.durand@example.com", firstName: "Pierre", lastName: "Durand", company: "DataFlow", tags: '["prospect"]' },
    { email: "sophie.bernard@example.com", firstName: "Sophie", lastName: "Bernard", company: "WebAgency", tags: '["client","formation"]' },
    { email: "luc.petit@example.com", firstName: "Luc", lastName: "Petit", company: "CloudNet", tags: '["prospect","newsletter"]' },
    { email: "emma.robert@example.com", firstName: "Emma", lastName: "Robert", company: "DigitalPlus", tags: '["client"]' },
    { email: "thomas.richard@example.com", firstName: "Thomas", lastName: "Richard", company: "SmartBiz", tags: '["prospect","formation"]' },
    { email: "julie.moreau@example.com", firstName: "Julie", lastName: "Moreau", company: "StartupLab", tags: '["client","vip"]' },
    { email: "nicolas.simon@example.com", firstName: "Nicolas", lastName: "Simon", company: "TechCorp", tags: '["newsletter"]' },
    { email: "camille.laurent@example.com", firstName: "Camille", lastName: "Laurent", company: "InnoSoft", tags: '["prospect","formation"]' },
  ];

  for (const contact of contacts) {
    await prisma.contact.upsert({
      where: { email: contact.email },
      update: {},
      create: contact,
    });
  }

  // Create sample templates
  const templates = [
    {
      name: "Newsletter Simple",
      category: "newsletter",
      subject: "Notre newsletter du mois",
      htmlContent: `<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:40px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#2563eb;padding:32px;text-align:center;">
<h1 style="color:#fff;margin:0;font-size:28px;">📬 Newsletter</h1>
</td></tr>
<tr><td style="padding:32px;">
<h2 style="color:#1e293b;margin-top:0;">Bonjour {{prenom}},</h2>
<p style="color:#475569;line-height:1.6;">Voici les dernières nouvelles de notre entreprise. Nous avons plein de choses passionnantes à partager avec vous ce mois-ci.</p>
<p style="color:#475569;line-height:1.6;">Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
<a href="#" style="display:inline-block;background:#2563eb;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;margin-top:16px;">En savoir plus</a>
</td></tr>
<tr><td style="background:#f8fafc;padding:24px;text-align:center;color:#94a3b8;font-size:12px;">
<p>© {{entreprise}} - Tous droits réservés</p>
<a href="#" style="color:#94a3b8;">Se désabonner</a>
</td></tr>
</table>
</td></tr></table>
</body></html>`,
    },
    {
      name: "Promotion Formation",
      category: "promotion",
      subject: "🎓 Offre spéciale sur nos formations",
      htmlContent: `<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:40px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:linear-gradient(135deg,#7c3aed,#2563eb);padding:40px;text-align:center;">
<h1 style="color:#fff;margin:0;font-size:32px;">🎓 Formation Spéciale</h1>
<p style="color:#e0e7ff;font-size:18px;margin-top:8px;">-30% cette semaine uniquement</p>
</td></tr>
<tr><td style="padding:32px;">
<h2 style="color:#1e293b;margin-top:0;">{{prenom}}, ne ratez pas cette opportunité !</h2>
<p style="color:#475569;line-height:1.6;">Nous vous proposons une remise exceptionnelle de <strong>30%</strong> sur l'ensemble de nos formations certifiantes.</p>
<div style="background:#f0f9ff;border-left:4px solid #2563eb;padding:16px;margin:20px 0;border-radius:0 6px 6px 0;">
<p style="color:#1e40af;margin:0;font-weight:bold;">✅ Formations éligibles CPF</p>
<p style="color:#1e40af;margin:4px 0 0;">✅ Certifications reconnues</p>
<p style="color:#1e40af;margin:4px 0 0;">✅ Accompagnement personnalisé</p>
</div>
<a href="#" style="display:inline-block;background:#7c3aed;color:#fff;padding:14px 32px;text-decoration:none;border-radius:6px;font-size:16px;font-weight:bold;">Découvrir nos formations</a>
</td></tr>
<tr><td style="background:#f8fafc;padding:24px;text-align:center;color:#94a3b8;font-size:12px;">
<p>© {{entreprise}} - Tous droits réservés</p>
<a href="#" style="color:#94a3b8;">Se désabonner</a>
</td></tr>
</table>
</td></tr></table>
</body></html>`,
    },
    {
      name: "Bienvenue",
      category: "welcome",
      subject: "Bienvenue chez {{entreprise}} !",
      htmlContent: `<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:40px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#059669;padding:40px;text-align:center;">
<h1 style="color:#fff;margin:0;font-size:32px;">👋 Bienvenue !</h1>
</td></tr>
<tr><td style="padding:32px;">
<h2 style="color:#1e293b;margin-top:0;">Bonjour {{prenom}},</h2>
<p style="color:#475569;line-height:1.6;">Nous sommes ravis de vous accueillir parmi nous ! Vous faites désormais partie de notre communauté.</p>
<p style="color:#475569;line-height:1.6;">N'hésitez pas à explorer notre catalogue de formations et à nous contacter si vous avez la moindre question.</p>
<a href="#" style="display:inline-block;background:#059669;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;margin-top:16px;">Explorer le catalogue</a>
</td></tr>
<tr><td style="background:#f8fafc;padding:24px;text-align:center;color:#94a3b8;font-size:12px;">
<p>© {{entreprise}} - Tous droits réservés</p>
</td></tr>
</table>
</td></tr></table>
</body></html>`,
    },
    {
      name: "Notification",
      category: "notification",
      subject: "Information importante",
      htmlContent: `<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:40px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;">
<tr><td style="background:#dc2626;padding:32px;text-align:center;">
<h1 style="color:#fff;margin:0;font-size:28px;">🔔 Notification</h1>
</td></tr>
<tr><td style="padding:32px;">
<h2 style="color:#1e293b;margin-top:0;">{{prenom}},</h2>
<p style="color:#475569;line-height:1.6;">Nous avons une information importante à vous communiquer.</p>
<div style="background:#fef2f2;border:1px solid #fecaca;padding:16px;border-radius:6px;margin:20px 0;">
<p style="color:#991b1b;margin:0;">Votre message de notification ici.</p>
</div>
<a href="#" style="display:inline-block;background:#dc2626;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;margin-top:16px;">Voir les détails</a>
</td></tr>
<tr><td style="background:#f8fafc;padding:24px;text-align:center;color:#94a3b8;font-size:12px;">
<p>© {{entreprise}} - Tous droits réservés</p>
<a href="#" style="color:#94a3b8;">Se désabonner</a>
</td></tr>
</table>
</td></tr></table>
</body></html>`,
    },
  ];

  for (const template of templates) {
    await prisma.template.upsert({
      where: { id: template.name.toLowerCase().replace(/\s+/g, "-") },
      update: {},
      create: {
        id: template.name.toLowerCase().replace(/\s+/g, "-"),
        ...template,
      },
    });
  }

  // Create sample campaigns
  const allContacts = await prisma.contact.findMany();

  const campaign1 = await prisma.campaign.upsert({
    where: { id: "campaign-1" },
    update: {},
    create: {
      id: "campaign-1",
      name: "Newsletter Mars 2026",
      subject: "Les nouveautés du mois de Mars",
      htmlContent: templates[0].htmlContent,
      status: "sent",
      sentAt: new Date("2026-03-15"),
      totalSent: 8,
      totalOpened: 5,
      totalClicked: 3,
      totalBounced: 0,
    },
  });

  const campaign2 = await prisma.campaign.upsert({
    where: { id: "campaign-2" },
    update: {},
    create: {
      id: "campaign-2",
      name: "Promo Formation IA",
      subject: "🎓 -30% sur nos formations Intelligence Artificielle",
      htmlContent: templates[1].htmlContent,
      status: "sent",
      sentAt: new Date("2026-03-28"),
      totalSent: 10,
      totalOpened: 7,
      totalClicked: 4,
      totalBounced: 1,
    },
  });

  await prisma.campaign.upsert({
    where: { id: "campaign-3" },
    update: {},
    create: {
      id: "campaign-3",
      name: "Newsletter Avril 2026",
      subject: "Nouveautés Avril - Formations Cybersécurité",
      htmlContent: templates[0].htmlContent,
      status: "draft",
    },
  });

  // Create campaign recipients for sent campaigns
  for (const contact of allContacts.slice(0, 8)) {
    await prisma.campaignRecipient.upsert({
      where: { campaignId_contactId: { campaignId: campaign1.id, contactId: contact.id } },
      update: {},
      create: {
        campaignId: campaign1.id,
        contactId: contact.id,
        status: Math.random() > 0.4 ? "opened" : "sent",
        sentAt: new Date("2026-03-15"),
        openedAt: Math.random() > 0.4 ? new Date("2026-03-15T14:30:00") : null,
      },
    });
  }

  for (const contact of allContacts) {
    await prisma.campaignRecipient.upsert({
      where: { campaignId_contactId: { campaignId: campaign2.id, contactId: contact.id } },
      update: {},
      create: {
        campaignId: campaign2.id,
        contactId: contact.id,
        status: Math.random() > 0.3 ? "opened" : "sent",
        sentAt: new Date("2026-03-28"),
        openedAt: Math.random() > 0.3 ? new Date("2026-03-28T10:15:00") : null,
      },
    });
  }

  console.log("✅ Base de données initialisée avec les données de démonstration !");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
