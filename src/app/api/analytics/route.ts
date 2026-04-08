import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function GET() {
  const [totalContacts, activeContacts, campaigns] = await Promise.all([
    prisma.contact.count(),
    prisma.contact.count({ where: { status: "active" } }),
    prisma.campaign.findMany({
      where: { status: "sent" },
      orderBy: { sentAt: "desc" },
    }),
  ]);

  const totalCampaigns = campaigns.length;
  const totalSent = campaigns.reduce((acc, c) => acc + c.totalSent, 0);
  const totalOpened = campaigns.reduce((acc, c) => acc + c.totalOpened, 0);
  const totalClicked = campaigns.reduce((acc, c) => acc + c.totalClicked, 0);
  const totalBounced = campaigns.reduce((acc, c) => acc + c.totalBounced, 0);

  const avgOpenRate = totalSent > 0 ? (totalOpened / totalSent) * 100 : 0;
  const avgClickRate = totalSent > 0 ? (totalClicked / totalSent) * 100 : 0;

  return NextResponse.json({
    totalCampaigns,
    totalSent,
    totalOpened,
    totalClicked,
    totalBounced,
    avgOpenRate,
    avgClickRate,
    totalContacts,
    activeContacts,
    campaigns: campaigns.map((c) => ({
      id: c.id,
      name: c.name,
      sentAt: c.sentAt,
      totalSent: c.totalSent,
      totalOpened: c.totalOpened,
      totalClicked: c.totalClicked,
      totalBounced: c.totalBounced,
    })),
  });
}
