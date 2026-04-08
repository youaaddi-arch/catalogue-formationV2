import {
  Users,
  Send,
  MousePointerClick,
  TrendingUp,
  Mail,
  ArrowUpRight,
  Clock,
} from "lucide-react";
import Link from "next/link";
import { prisma } from "@/lib/db";

async function getStats() {
  const [totalContacts, totalCampaigns, sentCampaigns, recentCampaigns] =
    await Promise.all([
      prisma.contact.count({ where: { status: "active" } }),
      prisma.campaign.count(),
      prisma.campaign.findMany({ where: { status: "sent" } }),
      prisma.campaign.findMany({
        orderBy: { createdAt: "desc" },
        take: 5,
        include: {
          _count: { select: { recipients: true } },
        },
      }),
    ]);

  const totalSent = sentCampaigns.reduce((acc, c) => acc + c.totalSent, 0);
  const totalOpened = sentCampaigns.reduce((acc, c) => acc + c.totalOpened, 0);
  const totalClicked = sentCampaigns.reduce(
    (acc, c) => acc + c.totalClicked,
    0
  );
  const avgOpenRate = totalSent > 0 ? ((totalOpened / totalSent) * 100).toFixed(1) : "0";
  const avgClickRate = totalSent > 0 ? ((totalClicked / totalSent) * 100).toFixed(1) : "0";

  return {
    totalContacts,
    totalCampaigns,
    totalSent,
    avgOpenRate,
    avgClickRate,
    recentCampaigns,
  };
}

export const dynamic = "force-dynamic";

export default async function Dashboard() {
  const stats = await getStats();

  const kpis = [
    {
      label: "Contacts actifs",
      value: stats.totalContacts.toLocaleString("fr-FR"),
      icon: Users,
      color: "bg-blue-500",
      lightColor: "bg-blue-50",
      textColor: "text-blue-600",
      change: "+12%",
    },
    {
      label: "Emails envoyés",
      value: stats.totalSent.toLocaleString("fr-FR"),
      icon: Send,
      color: "bg-green-500",
      lightColor: "bg-green-50",
      textColor: "text-green-600",
      change: "+8%",
    },
    {
      label: "Taux d'ouverture",
      value: `${stats.avgOpenRate}%`,
      icon: Mail,
      color: "bg-purple-500",
      lightColor: "bg-purple-50",
      textColor: "text-purple-600",
      change: "+2.3%",
    },
    {
      label: "Taux de clic",
      value: `${stats.avgClickRate}%`,
      icon: MousePointerClick,
      color: "bg-orange-500",
      lightColor: "bg-orange-50",
      textColor: "text-orange-600",
      change: "+1.5%",
    },
  ];

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Tableau de bord</h1>
        <p className="text-gray-500 mt-1">
          Vue d&apos;ensemble de vos campagnes d&apos;emailing
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {kpis.map((kpi) => (
          <div
            key={kpi.label}
            className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between mb-4">
              <div
                className={`w-12 h-12 ${kpi.lightColor} rounded-xl flex items-center justify-center`}
              >
                <kpi.icon className={`w-6 h-6 ${kpi.textColor}`} />
              </div>
              <span className="flex items-center gap-1 text-sm font-medium text-green-600">
                <TrendingUp className="w-4 h-4" />
                {kpi.change}
              </span>
            </div>
            <p className="text-3xl font-bold text-gray-900">{kpi.value}</p>
            <p className="text-sm text-gray-500 mt-1">{kpi.label}</p>
          </div>
        ))}
      </div>

      {/* Quick Actions + Recent Campaigns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Actions rapides</h2>
          <div className="space-y-3">
            <Link
              href="/campaigns/new"
              className="flex items-center gap-3 p-3 rounded-lg bg-blue-50 hover:bg-blue-100 transition-colors group"
            >
              <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                <Send className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1">
                <p className="font-medium text-gray-900">
                  Nouvelle campagne
                </p>
                <p className="text-sm text-gray-500">
                  Créer et envoyer un email
                </p>
              </div>
              <ArrowUpRight className="w-5 h-5 text-gray-400 group-hover:text-blue-600 transition-colors" />
            </Link>
            <Link
              href="/contacts"
              className="flex items-center gap-3 p-3 rounded-lg bg-green-50 hover:bg-green-100 transition-colors group"
            >
              <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center">
                <Users className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1">
                <p className="font-medium text-gray-900">
                  Ajouter des contacts
                </p>
                <p className="text-sm text-gray-500">
                  Importer ou créer des contacts
                </p>
              </div>
              <ArrowUpRight className="w-5 h-5 text-gray-400 group-hover:text-green-600 transition-colors" />
            </Link>
            <Link
              href="/templates"
              className="flex items-center gap-3 p-3 rounded-lg bg-purple-50 hover:bg-purple-100 transition-colors group"
            >
              <div className="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center">
                <Mail className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1">
                <p className="font-medium text-gray-900">
                  Voir les templates
                </p>
                <p className="text-sm text-gray-500">
                  Modèles d&apos;emails prêts à l&apos;emploi
                </p>
              </div>
              <ArrowUpRight className="w-5 h-5 text-gray-400 group-hover:text-purple-600 transition-colors" />
            </Link>
          </div>
        </div>

        {/* Recent Campaigns */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Campagnes récentes</h2>
            <Link
              href="/campaigns"
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              Voir tout
            </Link>
          </div>
          <div className="space-y-3">
            {stats.recentCampaigns.length === 0 ? (
              <p className="text-gray-500 text-center py-8">
                Aucune campagne pour le moment.{" "}
                <Link
                  href="/campaigns/new"
                  className="text-blue-600 hover:underline"
                >
                  Créer votre première campagne
                </Link>
              </p>
            ) : (
              stats.recentCampaigns.map((campaign) => (
                <div
                  key={campaign.id}
                  className="flex items-center gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      campaign.status === "sent"
                        ? "bg-green-100"
                        : campaign.status === "draft"
                        ? "bg-gray-100"
                        : "bg-yellow-100"
                    }`}
                  >
                    {campaign.status === "sent" ? (
                      <Send className="w-5 h-5 text-green-600" />
                    ) : (
                      <Clock className="w-5 h-5 text-gray-500" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">
                      {campaign.name}
                    </p>
                    <p className="text-sm text-gray-500">
                      {campaign._count.recipients} destinataires
                    </p>
                  </div>
                  <div className="text-right">
                    <span
                      className={`badge ${
                        campaign.status === "sent"
                          ? "badge-green"
                          : campaign.status === "draft"
                          ? "badge-gray"
                          : "badge-yellow"
                      }`}
                    >
                      {campaign.status === "sent"
                        ? "Envoyée"
                        : campaign.status === "draft"
                        ? "Brouillon"
                        : "Planifiée"}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
