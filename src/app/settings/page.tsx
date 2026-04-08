"use client";

import { useState, useEffect } from "react";
import { Settings, Save, TestTube, Check, AlertCircle } from "lucide-react";
import toast from "react-hot-toast";

interface SettingsData {
  smtpHost: string;
  smtpPort: number;
  smtpUser: string;
  smtpPass: string;
  fromEmail: string;
  fromName: string;
  company: string;
  website: string;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsData>({
    smtpHost: "",
    smtpPort: 587,
    smtpUser: "",
    smtpPass: "",
    fromEmail: "",
    fromName: "",
    company: "",
    website: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    fetch("/api/settings")
      .then((r) => r.json())
      .then((data) => {
        if (data) setSettings(data);
      })
      .catch(() => null)
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      if (!res.ok) throw new Error("Erreur");
      toast.success("Paramètres sauvegardés !");
    } catch {
      toast.error("Erreur lors de la sauvegarde");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!settings.smtpHost || !settings.fromEmail) {
      toast.error("Configurez d'abord vos paramètres SMTP");
      return;
    }
    setTesting(true);
    try {
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "test" }),
      });
      const data = await res.json();
      if (res.ok) {
        toast.success("Connexion SMTP réussie !");
      } else {
        toast.error(data.error || "Échec de la connexion SMTP");
      }
    } catch {
      toast.error("Erreur lors du test");
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="animate-fade-in">
        <h1 className="text-2xl font-bold text-gray-900 mb-8">Paramètres</h1>
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-500">
          Chargement...
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in max-w-3xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Paramètres</h1>
        <p className="text-gray-500 mt-1">
          Configurez votre plateforme d&apos;emailing
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* SMTP Configuration */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center">
              <Settings className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">Configuration SMTP</h2>
              <p className="text-sm text-gray-500">
                Paramètres du serveur d&apos;envoi d&apos;emails
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Serveur SMTP
                </label>
                <input
                  type="text"
                  value={settings.smtpHost}
                  onChange={(e) =>
                    setSettings({ ...settings, smtpHost: e.target.value })
                  }
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="smtp.gmail.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Port
                </label>
                <input
                  type="number"
                  value={settings.smtpPort}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      smtpPort: parseInt(e.target.value) || 587,
                    })
                  }
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="587"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Utilisateur SMTP
                </label>
                <input
                  type="text"
                  value={settings.smtpUser}
                  onChange={(e) =>
                    setSettings({ ...settings, smtpUser: e.target.value })
                  }
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="votre-email@gmail.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Mot de passe SMTP
                </label>
                <input
                  type="password"
                  value={settings.smtpPass}
                  onChange={(e) =>
                    setSettings({ ...settings, smtpPass: e.target.value })
                  }
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-yellow-600 mt-0.5" />
                <div className="text-sm text-yellow-800">
                  <p className="font-medium">Gmail</p>
                  <p>
                    Utilisez smtp.gmail.com:587 avec un mot de passe
                    d&apos;application.
                  </p>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={handleTest}
              disabled={testing}
              className="flex items-center gap-2 px-4 py-2.5 border border-blue-300 text-blue-600 rounded-lg text-sm font-medium hover:bg-blue-50 disabled:opacity-50"
            >
              <TestTube className="w-4 h-4" />
              {testing ? "Test en cours..." : "Tester la connexion"}
            </button>
          </div>
        </div>

        {/* Sender Info */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">
            Informations d&apos;expéditeur
          </h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email d&apos;expédition
                </label>
                <input
                  type="email"
                  value={settings.fromEmail}
                  onChange={(e) =>
                    setSettings({ ...settings, fromEmail: e.target.value })
                  }
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="contact@entreprise.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nom d&apos;expéditeur
                </label>
                <input
                  type="text"
                  value={settings.fromName}
                  onChange={(e) =>
                    setSettings({ ...settings, fromName: e.target.value })
                  }
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Mon Entreprise"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Company Info */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Entreprise</h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nom de l&apos;entreprise
                </label>
                <input
                  type="text"
                  value={settings.company}
                  onChange={(e) =>
                    setSettings({ ...settings, company: e.target.value })
                  }
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Mon Entreprise"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Site web
                </label>
                <input
                  type="url"
                  value={settings.website}
                  onChange={(e) =>
                    setSettings({ ...settings, website: e.target.value })
                  }
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="https://www.exemple.com"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? (
              "Sauvegarde..."
            ) : (
              <>
                <Save className="w-4 h-4" />
                Sauvegarder les paramètres
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
