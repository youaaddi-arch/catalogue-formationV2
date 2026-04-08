"use client";

import { useState, useEffect, useCallback } from "react";
import {
  FileText,
  Plus,
  Eye,
  Edit2,
  Trash2,
  X,
  Save,
  Copy,
} from "lucide-react";
import toast from "react-hot-toast";

interface Template {
  id: string;
  name: string;
  category: string;
  subject: string;
  htmlContent: string;
  createdAt: string;
}

const categories = [
  { key: "all", label: "Tous" },
  { key: "newsletter", label: "Newsletter" },
  { key: "promotion", label: "Promotion" },
  { key: "welcome", label: "Bienvenue" },
  { key: "notification", label: "Notification" },
  { key: "general", label: "Général" },
];

const categoryColors: Record<string, string> = {
  newsletter: "badge-blue",
  promotion: "badge-purple",
  welcome: "badge-green",
  notification: "badge-red",
  general: "badge-gray",
};

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [showEditor, setShowEditor] = useState(false);
  const [showPreview, setShowPreview] = useState<Template | null>(null);
  const [editTemplate, setEditTemplate] = useState<Template | null>(null);

  const [form, setForm] = useState({
    name: "",
    category: "general",
    subject: "",
    htmlContent: "",
  });

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await fetch(
        `/api/templates${filter !== "all" ? `?category=${filter}` : ""}`
      );
      const data = await res.json();
      setTemplates(data);
    } catch {
      toast.error("Erreur lors du chargement");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const method = editTemplate ? "PUT" : "POST";
      const body = editTemplate ? { ...form, id: editTemplate.id } : form;

      const res = await fetch("/api/templates", {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error("Erreur");
      toast.success(
        editTemplate ? "Template mis à jour !" : "Template créé !"
      );
      setShowEditor(false);
      setEditTemplate(null);
      setForm({ name: "", category: "general", subject: "", htmlContent: "" });
      fetchTemplates();
    } catch {
      toast.error("Erreur lors de la sauvegarde");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Supprimer ce template ?")) return;
    try {
      await fetch("/api/templates", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id }),
      });
      toast.success("Template supprimé");
      fetchTemplates();
    } catch {
      toast.error("Erreur lors de la suppression");
    }
  };

  const handleDuplicate = async (template: Template) => {
    try {
      await fetch("/api/templates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: `${template.name} (copie)`,
          category: template.category,
          subject: template.subject,
          htmlContent: template.htmlContent,
        }),
      });
      toast.success("Template dupliqué !");
      fetchTemplates();
    } catch {
      toast.error("Erreur lors de la duplication");
    }
  };

  const openEdit = (template: Template) => {
    setEditTemplate(template);
    setForm({
      name: template.name,
      category: template.category,
      subject: template.subject,
      htmlContent: template.htmlContent,
    });
    setShowEditor(true);
  };

  const openNew = () => {
    setEditTemplate(null);
    setForm({ name: "", category: "general", subject: "", htmlContent: "" });
    setShowEditor(true);
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Templates</h1>
          <p className="text-gray-500 mt-1">
            Modèles d&apos;emails prêts à l&apos;emploi
          </p>
        </div>
        <button
          onClick={openNew}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Nouveau template
        </button>
      </div>

      {/* Categories */}
      <div className="flex items-center gap-1 bg-white border border-gray-200 rounded-lg p-1 mb-6 w-fit">
        {categories.map((cat) => (
          <button
            key={cat.key}
            onClick={() => setFilter(cat.key)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              filter === cat.key
                ? "bg-blue-600 text-white"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Templates Grid */}
      {loading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-500">
          Chargement...
        </div>
      ) : templates.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 mb-2">Aucun template trouvé</p>
          <button
            onClick={openNew}
            className="text-blue-600 hover:underline text-sm"
          >
            Créer votre premier template
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {templates.map((template) => (
            <div
              key={template.id}
              className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow group"
            >
              {/* Preview thumbnail */}
              <div
                className="h-48 bg-gray-50 overflow-hidden relative cursor-pointer"
                onClick={() => setShowPreview(template)}
              >
                <div
                  className="transform scale-[0.4] origin-top-left w-[250%]"
                  dangerouslySetInnerHTML={{
                    __html: template.htmlContent,
                  }}
                />
                <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-white/80" />
                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/20">
                  <div className="bg-white rounded-lg px-4 py-2 shadow-lg flex items-center gap-2">
                    <Eye className="w-4 h-4" />
                    Aperçu
                  </div>
                </div>
              </div>
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-gray-900 truncate">
                    {template.name}
                  </h3>
                  <span
                    className={`badge ${
                      categoryColors[template.category] || "badge-gray"
                    }`}
                  >
                    {template.category}
                  </span>
                </div>
                {template.subject && (
                  <p className="text-sm text-gray-500 truncate mb-3">
                    {template.subject}
                  </p>
                )}
                <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
                  <button
                    onClick={() => openEdit(template)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                    Modifier
                  </button>
                  <button
                    onClick={() => handleDuplicate(template)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    Dupliquer
                  </button>
                  <button
                    onClick={() => handleDelete(template.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-md transition-colors ml-auto"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Template Editor Modal */}
      {showEditor && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl w-full max-w-4xl mx-4 max-h-[90vh] flex flex-col animate-fade-in">
            <div className="flex items-center justify-between p-6 border-b">
              <h2 className="text-lg font-semibold">
                {editTemplate ? "Modifier le template" : "Nouveau template"}
              </h2>
              <button
                onClick={() => {
                  setShowEditor(false);
                  setEditTemplate(null);
                }}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="flex-1 overflow-auto p-6">
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nom du template *
                  </label>
                  <input
                    type="text"
                    required
                    value={form.name}
                    onChange={(e) =>
                      setForm({ ...form, name: e.target.value })
                    }
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Mon template"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Catégorie
                  </label>
                  <select
                    value={form.category}
                    onChange={(e) =>
                      setForm({ ...form, category: e.target.value })
                    }
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="general">Général</option>
                    <option value="newsletter">Newsletter</option>
                    <option value="promotion">Promotion</option>
                    <option value="welcome">Bienvenue</option>
                    <option value="notification">Notification</option>
                  </select>
                </div>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Objet par défaut
                </label>
                <input
                  type="text"
                  value={form.subject}
                  onChange={(e) =>
                    setForm({ ...form, subject: e.target.value })
                  }
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Objet de l'email"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Contenu HTML *
                </label>
                <textarea
                  required
                  value={form.htmlContent}
                  onChange={(e) =>
                    setForm({ ...form, htmlContent: e.target.value })
                  }
                  className="w-full h-64 px-3 py-2.5 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                  placeholder="<html>...</html>"
                />
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowEditor(false);
                    setEditTemplate(null);
                  }}
                  className="px-4 py-2.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
                >
                  <Save className="w-4 h-4" />
                  {editTemplate ? "Mettre à jour" : "Créer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {showPreview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl w-full max-w-3xl mx-4 max-h-[90vh] flex flex-col animate-fade-in">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-lg font-semibold">
                Aperçu : {showPreview.name}
              </h2>
              <button
                onClick={() => setShowPreview(null)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-auto p-4">
              <div
                dangerouslySetInnerHTML={{
                  __html: showPreview.htmlContent,
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
