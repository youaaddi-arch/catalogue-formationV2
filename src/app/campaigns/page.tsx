"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Send,
  Plus,
  Search,
  Clock,
  CheckCircle2,
  FileText,
  Trash2,
  Eye,
  BarChart3,
  AlertCircle,
} from "lucide-react";
import toast from "react-hot-toast";

interface Campaign {
  id: string;
  name: string;
  subject: string;
  status: string;
  totalSent: number;
  totalOpened: number;
  totalClicked: number;
  totalBounced: number;
  sentAt: string | null;
  createdAt: string;
  _count: { recipients: number };
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  const fetchCampaigns = useCallback(async () => {
    try {
      const res = await fetch(
        `/api/campaigns?status=${filter}&search=${encodeURIComponent(search)}`
      );
      const data = await res.json();
      setCampaigns(data);
    } catch {
      toast.error("Erreur lors du chargement");
    } finally {
      setLoading(false);
    }
  }, [filter, search]);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  const handleDelete = async (id: string) => {
    if (!confirm("Supprimer cette campagne ?")) return;
    try {
      await fetch("/api/campaigns", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id }),
      });
      toast.success("Campagne supprimée");
      fetchCampaigns();
    } catch {
      toast.error("Erreur lors de la suppression");
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "sent":
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case "draft":
        return <FileText className="w-5 h-5 text-gray-400" />;
      case "sending":
        return <Send className="w-5 h-5 text-blue-500 animate-pulse" />;
      case "scheduled":
        return <Clock className="w-5 h-5 text-yellow-500" />;
      case "failed":
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <FileText className="w-5 h-5 text-gray-400" />;
    }
  };

  const statusLabel = (status: string) => {
    const map: Record<string, { label: string; class: string }> = {
      draft: { label: "Brouillon", class: "badge-gray" },
      scheduled: { label: "Planifiée", class: "badge-yellow" },
      sending: { label: "En cours", class: "badge-blue" },
      sent: { label: "Envoyée", class: "badge-green" },
      failed: { label: "Échouée", class: "badge-red" },
    };
    const s = map[status] || map.draft;
    return <span className={`badge ${s.class}`}>{s.label}</span>;
  };

  const formatDate = (date: string | null) => {
    if (!date) return "-";
    return new Date(date).toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Campagnes</h1>
          <p className="text-gray-500 mt-1">
            Créez et gérez vos campagnes d&apos;emailing
          </p>
        </div>
        <Link
          href="/campaigns/new"
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Nouvelle campagne
        </Link>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex items-center gap-1 bg-white border border-gray-200 rounded-lg p-1">
          {[
            { key: "all", label: "Toutes" },
            { key: "draft", label: "Brouillons" },
            { key: "sent", label: "Envoyées" },
            { key: "scheduled", label: "Planifiées" },
          ].map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                filter === f.key
                  ? "bg-blue-600 text-white"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Rechercher une campagne..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Campaigns List */}
      <div className="space-y-4">
        {loading ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-500">
            Chargement...
          </div>
        ) : campaigns.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <Send className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 mb-2">Aucune campagne trouvée</p>
            <Link
              href="/campaigns/new"
              className="text-blue-600 hover:underline text-sm"
            >
              Créer votre première campagne
            </Link>
          </div>
        ) : (
          campaigns.map((campaign) => (
            <div
              key={campaign.id}
              className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start gap-4">
                <div className="mt-1">{statusIcon(campaign.status)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="font-semibold text-gray-900 truncate">
                      {campaign.name}
                    </h3>
                    {statusLabel(campaign.status)}
                  </div>
                  <p className="text-sm text-gray-500 truncate mb-3">
                    Objet : {campaign.subject}
                  </p>
                  <div className="flex items-center gap-6 text-sm text-gray-500">
                    <span>
                      {campaign._count.recipients} destinataire
                      {campaign._count.recipients !== 1 ? "s" : ""}
                    </span>
                    {campaign.status === "sent" && (
                      <>
                        <span className="flex items-center gap-1">
                          <Eye className="w-4 h-4" />
                          {campaign.totalSent > 0
                            ? (
                                (campaign.totalOpened / campaign.totalSent) *
                                100
                              ).toFixed(1)
                            : 0}
                          % ouverture
                        </span>
                        <span className="flex items-center gap-1">
                          <BarChart3 className="w-4 h-4" />
                          {campaign.totalSent > 0
                            ? (
                                (campaign.totalClicked / campaign.totalSent) *
                                100
                              ).toFixed(1)
                            : 0}
                          % clics
                        </span>
                      </>
                    )}
                    <span>
                      {campaign.sentAt
                        ? `Envoyée le ${formatDate(campaign.sentAt)}`
                        : `Créée le ${formatDate(campaign.createdAt)}`}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {campaign.status === "draft" && (
                    <Link
                      href={`/campaigns/new?edit=${campaign.id}`}
                      className="px-3 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    >
                      Modifier
                    </Link>
                  )}
                  <button
                    onClick={() => handleDelete(campaign.id)}
                    className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Supprimer"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
