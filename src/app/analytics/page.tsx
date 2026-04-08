"use client";

import { useState, useEffect } from "react";
import {
  BarChart3,
  TrendingUp,
  Mail,
  MousePointerClick,
  Users,
  Send,
  Eye,
  AlertTriangle,
} from "lucide-react";

interface AnalyticsData {
  totalCampaigns: number;
  totalSent: number;
  totalOpened: number;
  totalClicked: number;
  totalBounced: number;
  avgOpenRate: number;
  avgClickRate: number;
  totalContacts: number;
  activeContacts: number;
  campaigns: {
    id: string;
    name: string;
    sentAt: string | null;
    totalSent: number;
    totalOpened: number;
    totalClicked: number;
    totalBounced: number;
  }[];
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/analytics")
      .then((r) => r.json())
      .then(setData)
      .catch(() => null)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="animate-fade-in">
        <h1 className="text-2xl font-bold text-gray-900 mb-8">Analytiques</h1>
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-500">
          Chargement des données...
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="animate-fade-in">
        <h1 className="text-2xl font-bold text-gray-900 mb-8">Analytiques</h1>
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-500">
          Erreur lors du chargement des données
        </div>
      </div>
    );
  }

  const kpis = [
    {
      label: "Emails envoyés",
      value: data.totalSent,
      icon: Send,
      color: "text-blue-600",
      bg: "bg-blue-50",
    },
    {
      label: "Taux d'ouverture moyen",
      value: `${data.avgOpenRate.toFixed(1)}%`,
      icon: Eye,
      color: "text-green-600",
      bg: "bg-green-50",
    },
    {
      label: "Taux de clic moyen",
      value: `${data.avgClickRate.toFixed(1)}%`,
      icon: MousePointerClick,
      color: "text-purple-600",
      bg: "bg-purple-50",
    },
    {
      label: "Taux de rebond",
      value:
        data.totalSent > 0
          ? `${((data.totalBounced / data.totalSent) * 100).toFixed(1)}%`
          : "0%",
      icon: AlertTriangle,
      color: "text-red-600",
      bg: "bg-red-50",
    },
  ];

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Analytiques</h1>
        <p className="text-gray-500 mt-1">
          Performance de vos campagnes d&apos;emailing
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {kpis.map((kpi) => (
          <div
            key={kpi.label}
            className="bg-white rounded-xl border border-gray-200 p-6"
          >
            <div className="flex items-center gap-3 mb-3">
              <div
                className={`w-10 h-10 ${kpi.bg} rounded-lg flex items-center justify-center`}
              >
                <kpi.icon className={`w-5 h-5 ${kpi.color}`} />
              </div>
              <span className="text-sm text-gray-500">{kpi.label}</span>
            </div>
            <p className="text-3xl font-bold text-gray-900">
              {typeof kpi.value === "number"
                ? kpi.value.toLocaleString("fr-FR")
                : kpi.value}
            </p>
          </div>
        ))}
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Contacts Overview */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-blue-600" />
            Contacts
          </h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Total contacts</span>
              <span className="font-semibold">
                {data.totalContacts.toLocaleString("fr-FR")}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Contacts actifs</span>
              <span className="font-semibold text-green-600">
                {data.activeContacts.toLocaleString("fr-FR")}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Taux actif</span>
              <span className="font-semibold">
                {data.totalContacts > 0
                  ? (
                      (data.activeContacts / data.totalContacts) *
                      100
                    ).toFixed(1)
                  : 0}
                %
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
              <div
                className="bg-green-500 h-2.5 rounded-full transition-all"
                style={{
                  width: `${
                    data.totalContacts > 0
                      ? (data.activeContacts / data.totalContacts) * 100
                      : 0
                  }%`,
                }}
              />
            </div>
          </div>
        </div>

        {/* Campaign Overview */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Mail className="w-5 h-5 text-purple-600" />
            Résumé des campagnes
          </h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Total campagnes</span>
              <span className="font-semibold">{data.totalCampaigns}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Total ouvertures</span>
              <span className="font-semibold text-green-600">
                {data.totalOpened.toLocaleString("fr-FR")}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Total clics</span>
              <span className="font-semibold text-blue-600">
                {data.totalClicked.toLocaleString("fr-FR")}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Total rebonds</span>
              <span className="font-semibold text-red-600">
                {data.totalBounced}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Campaign Performance Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-600" />
            Performance par campagne
          </h2>
        </div>
        {data.campaigns.length === 0 ? (
          <div className="p-12 text-center text-gray-500">
            Aucune campagne envoyée pour le moment
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="py-3 px-6 text-left text-xs font-semibold text-gray-500 uppercase">
                  Campagne
                </th>
                <th className="py-3 px-6 text-center text-xs font-semibold text-gray-500 uppercase">
                  Envoyés
                </th>
                <th className="py-3 px-6 text-center text-xs font-semibold text-gray-500 uppercase">
                  Ouverts
                </th>
                <th className="py-3 px-6 text-center text-xs font-semibold text-gray-500 uppercase">
                  Taux ouverture
                </th>
                <th className="py-3 px-6 text-center text-xs font-semibold text-gray-500 uppercase">
                  Clics
                </th>
                <th className="py-3 px-6 text-center text-xs font-semibold text-gray-500 uppercase">
                  Taux clic
                </th>
                <th className="py-3 px-6 text-center text-xs font-semibold text-gray-500 uppercase">
                  Rebonds
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.campaigns.map((campaign) => {
                const openRate =
                  campaign.totalSent > 0
                    ? ((campaign.totalOpened / campaign.totalSent) * 100).toFixed(1)
                    : "0";
                const clickRate =
                  campaign.totalSent > 0
                    ? ((campaign.totalClicked / campaign.totalSent) * 100).toFixed(1)
                    : "0";

                return (
                  <tr key={campaign.id} className="hover:bg-gray-50">
                    <td className="py-4 px-6">
                      <div>
                        <p className="font-medium text-gray-900">
                          {campaign.name}
                        </p>
                        <p className="text-xs text-gray-400">
                          {campaign.sentAt
                            ? new Date(campaign.sentAt).toLocaleDateString("fr-FR")
                            : "-"}
                        </p>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-center font-medium">
                      {campaign.totalSent}
                    </td>
                    <td className="py-4 px-6 text-center text-green-600 font-medium">
                      {campaign.totalOpened}
                    </td>
                    <td className="py-4 px-6 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-16 bg-gray-200 rounded-full h-1.5">
                          <div
                            className="bg-green-500 h-1.5 rounded-full"
                            style={{ width: `${openRate}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium">
                          {openRate}%
                        </span>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-center text-blue-600 font-medium">
                      {campaign.totalClicked}
                    </td>
                    <td className="py-4 px-6 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-16 bg-gray-200 rounded-full h-1.5">
                          <div
                            className="bg-blue-500 h-1.5 rounded-full"
                            style={{ width: `${clickRate}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium">
                          {clickRate}%
                        </span>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-center text-red-500 font-medium">
                      {campaign.totalBounced}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
