"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  Send,
  Save,
  Eye,
  Users,
  FileText,
  ChevronRight,
  X,
  Check,
} from "lucide-react";
import Link from "next/link";
import toast from "react-hot-toast";

interface Contact {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  company: string;
}

interface Template {
  id: string;
  name: string;
  category: string;
  subject: string;
  htmlContent: string;
}

export default function NewCampaignPage() {
  return (
    <Suspense fallback={<div className="p-12 text-center text-gray-500">Chargement...</div>}>
      <NewCampaignContent />
    </Suspense>
  );
}

function NewCampaignContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const editId = searchParams.get("edit");

  const [step, setStep] = useState(1);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedContacts, setSelectedContacts] = useState<string[]>([]);
  const [selectAll, setSelectAll] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [sending, setSending] = useState(false);

  const [form, setForm] = useState({
    name: "",
    subject: "",
    htmlContent: "",
  });

  useEffect(() => {
    // Load contacts and templates
    Promise.all([
      fetch("/api/contacts").then((r) => r.json()),
      fetch("/api/templates").then((r) => r.json()),
    ]).then(([contactsData, templatesData]) => {
      setContacts(contactsData);
      setTemplates(templatesData);
    });

    // Load campaign if editing
    if (editId) {
      fetch(`/api/campaigns?id=${editId}`)
        .then((r) => r.json())
        .then((data) => {
          if (data && !Array.isArray(data)) {
            setForm({
              name: data.name,
              subject: data.subject,
              htmlContent: data.htmlContent,
            });
            if (data.recipients) {
              setSelectedContacts(
                data.recipients.map((r: { contactId: string }) => r.contactId)
              );
            }
          }
        });
    }
  }, [editId]);

  const handleSelectTemplate = (template: Template) => {
    setForm({
      ...form,
      subject: template.subject || form.subject,
      htmlContent: template.htmlContent,
    });
    toast.success(`Template "${template.name}" sélectionné`);
  };

  const toggleContact = (id: string) => {
    setSelectedContacts((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    if (selectAll) {
      setSelectedContacts([]);
    } else {
      setSelectedContacts(contacts.map((c) => c.id));
    }
    setSelectAll(!selectAll);
  };

  const handleSaveDraft = async () => {
    try {
      const method = editId ? "PUT" : "POST";
      const body = {
        ...(editId ? { id: editId } : {}),
        ...form,
        status: "draft",
        recipientIds: selectedContacts,
      };

      const res = await fetch("/api/campaigns", {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error("Erreur");
      toast.success("Brouillon sauvegardé !");
      router.push("/campaigns");
    } catch {
      toast.error("Erreur lors de la sauvegarde");
    }
  };

  const handleSend = async () => {
    if (selectedContacts.length === 0) {
      toast.error("Sélectionnez au moins un destinataire");
      return;
    }
    if (!form.subject.trim()) {
      toast.error("L'objet est requis");
      return;
    }
    if (!form.htmlContent.trim()) {
      toast.error("Le contenu est requis");
      return;
    }

    setSending(true);
    try {
      // Save campaign first
      const saveMethod = editId ? "PUT" : "POST";
      const saveBody = {
        ...(editId ? { id: editId } : {}),
        ...form,
        status: "sending",
        recipientIds: selectedContacts,
      };

      const saveRes = await fetch("/api/campaigns", {
        method: saveMethod,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(saveBody),
      });

      if (!saveRes.ok) throw new Error("Erreur de sauvegarde");
      const campaign = await saveRes.json();

      // Send campaign
      const sendRes = await fetch("/api/campaigns/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ campaignId: campaign.id }),
      });

      if (!sendRes.ok) {
        const error = await sendRes.json();
        throw new Error(error.error || "Erreur d'envoi");
      }

      toast.success("Campagne envoyée avec succès !");
      router.push("/campaigns");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erreur d'envoi");
    } finally {
      setSending(false);
    }
  };

  const steps = [
    { num: 1, label: "Informations", icon: FileText },
    { num: 2, label: "Contenu", icon: FileText },
    { num: 3, label: "Destinataires", icon: Users },
    { num: 4, label: "Envoi", icon: Send },
  ];

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Link
          href="/campaigns"
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">
            {editId ? "Modifier la campagne" : "Nouvelle campagne"}
          </h1>
        </div>
        <button
          onClick={handleSaveDraft}
          className="flex items-center gap-2 px-4 py-2.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <Save className="w-4 h-4" />
          Sauvegarder
        </button>
      </div>

      {/* Steps */}
      <div className="flex items-center gap-2 mb-8 bg-white rounded-xl border border-gray-200 p-4">
        {steps.map((s, i) => (
          <div key={s.num} className="flex items-center">
            <button
              onClick={() => setStep(s.num)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                step === s.num
                  ? "bg-blue-600 text-white"
                  : step > s.num
                  ? "bg-green-50 text-green-700"
                  : "text-gray-500 hover:bg-gray-100"
              }`}
            >
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  step > s.num
                    ? "bg-green-500 text-white"
                    : step === s.num
                    ? "bg-white/20 text-current"
                    : "bg-gray-200 text-gray-500"
                }`}
              >
                {step > s.num ? <Check className="w-3 h-3" /> : s.num}
              </div>
              {s.label}
            </button>
            {i < steps.length - 1 && (
              <ChevronRight className="w-5 h-5 text-gray-300 mx-1" />
            )}
          </div>
        ))}
      </div>

      {/* Step 1: Campaign Info */}
      {step === 1 && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 max-w-2xl">
          <h2 className="text-lg font-semibold mb-6">
            Informations de la campagne
          </h2>
          <div className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nom de la campagne *
              </label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Ex: Newsletter Avril 2026"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Objet de l&apos;email *
              </label>
              <input
                type="text"
                value={form.subject}
                onChange={(e) =>
                  setForm({ ...form, subject: e.target.value })
                }
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Ex: Découvrez nos nouvelles formations !"
              />
              <p className="text-xs text-gray-400 mt-1">
                Variables disponibles : {"{{prenom}}"}, {"{{nom}}"},{" "}
                {"{{entreprise}}"}
              </p>
            </div>
          </div>
          <div className="flex justify-end mt-8">
            <button
              onClick={() => setStep(2)}
              disabled={!form.name || !form.subject}
              className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Suivant
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Content */}
      {step === 2 && (
        <div className="space-y-6">
          {/* Template Selection */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold mb-4">
              Choisir un template (optionnel)
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {templates.map((template) => (
                <button
                  key={template.id}
                  onClick={() => handleSelectTemplate(template)}
                  className="border border-gray-200 rounded-lg p-4 text-left hover:border-blue-500 hover:bg-blue-50 transition-all"
                >
                  <div className="w-full h-20 bg-gradient-to-br from-gray-100 to-gray-200 rounded-md mb-3 flex items-center justify-center">
                    <FileText className="w-8 h-8 text-gray-400" />
                  </div>
                  <p className="font-medium text-sm text-gray-900 truncate">
                    {template.name}
                  </p>
                  <p className="text-xs text-gray-500 capitalize">
                    {template.category}
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* HTML Editor */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Contenu HTML</h2>
              <button
                onClick={() => setShowPreview(true)}
                className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-lg"
              >
                <Eye className="w-4 h-4" />
                Aperçu
              </button>
            </div>
            <textarea
              value={form.htmlContent}
              onChange={(e) =>
                setForm({ ...form, htmlContent: e.target.value })
              }
              className="w-full h-96 px-4 py-3 border border-gray-300 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
              placeholder="Collez votre HTML ici ou sélectionnez un template ci-dessus..."
            />
            <p className="text-xs text-gray-400 mt-2">
              Variables : {"{{prenom}}"}, {"{{nom}}"}, {"{{entreprise}}"},{" "}
              {"{{email}}"}
            </p>
          </div>

          <div className="flex justify-between">
            <button
              onClick={() => setStep(1)}
              className="px-6 py-2.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Précédent
            </button>
            <button
              onClick={() => setStep(3)}
              disabled={!form.htmlContent}
              className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Suivant
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Recipients */}
      {step === 3 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold">
              Sélectionner les destinataires
            </h2>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={selectAll}
                  onChange={handleSelectAll}
                  className="rounded border-gray-300"
                />
                Tout sélectionner
              </label>
              <span className="badge badge-blue">
                {selectedContacts.length} sélectionné
                {selectedContacts.length !== 1 ? "s" : ""}
              </span>
            </div>
          </div>

          <div className="space-y-2 max-h-96 overflow-y-auto">
            {contacts.map((contact) => (
              <label
                key={contact.id}
                className={`flex items-center gap-4 p-3 rounded-lg cursor-pointer transition-colors ${
                  selectedContacts.includes(contact.id)
                    ? "bg-blue-50 border border-blue-200"
                    : "hover:bg-gray-50 border border-transparent"
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedContacts.includes(contact.id)}
                  onChange={() => toggleContact(contact.id)}
                  className="rounded border-gray-300"
                />
                <div className="w-9 h-9 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-semibold text-sm">
                  {contact.firstName?.[0] ||
                    contact.email[0].toUpperCase()}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-900">
                    {contact.firstName} {contact.lastName}
                  </p>
                  <p className="text-sm text-gray-500">{contact.email}</p>
                </div>
                <span className="text-sm text-gray-400">
                  {contact.company}
                </span>
              </label>
            ))}
          </div>

          <div className="flex justify-between mt-8">
            <button
              onClick={() => setStep(2)}
              className="px-6 py-2.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Précédent
            </button>
            <button
              onClick={() => setStep(4)}
              disabled={selectedContacts.length === 0}
              className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Suivant
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Review & Send */}
      {step === 4 && (
        <div className="space-y-6 max-w-2xl">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold mb-6">
              Récapitulatif de la campagne
            </h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between py-3 border-b border-gray-100">
                <span className="text-sm text-gray-500">Nom</span>
                <span className="font-medium">{form.name}</span>
              </div>
              <div className="flex items-center justify-between py-3 border-b border-gray-100">
                <span className="text-sm text-gray-500">Objet</span>
                <span className="font-medium">{form.subject}</span>
              </div>
              <div className="flex items-center justify-between py-3 border-b border-gray-100">
                <span className="text-sm text-gray-500">Destinataires</span>
                <span className="badge badge-blue">
                  {selectedContacts.length} contact
                  {selectedContacts.length !== 1 ? "s" : ""}
                </span>
              </div>
              <div className="flex items-center justify-between py-3">
                <span className="text-sm text-gray-500">Contenu</span>
                <button
                  onClick={() => setShowPreview(true)}
                  className="text-sm text-blue-600 hover:underline flex items-center gap-1"
                >
                  <Eye className="w-4 h-4" />
                  Voir l&apos;aperçu
                </button>
              </div>
            </div>
          </div>

          <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
            <p className="text-sm text-yellow-800">
              <strong>Note :</strong> Assurez-vous d&apos;avoir configuré vos
              paramètres SMTP dans{" "}
              <Link href="/settings" className="underline">
                Paramètres
              </Link>{" "}
              avant d&apos;envoyer.
            </p>
          </div>

          <div className="flex justify-between">
            <button
              onClick={() => setStep(3)}
              className="px-6 py-2.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Précédent
            </button>
            <div className="flex items-center gap-3">
              <button
                onClick={handleSaveDraft}
                className="flex items-center gap-2 px-6 py-2.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <Save className="w-4 h-4" />
                Sauvegarder comme brouillon
              </button>
              <button
                onClick={handleSend}
                disabled={sending}
                className="flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg text-sm font-bold hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                <Send className="w-4 h-4" />
                {sending ? "Envoi en cours..." : "Envoyer maintenant"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {showPreview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl w-full max-w-3xl mx-4 max-h-[90vh] flex flex-col animate-fade-in">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-lg font-semibold">Aperçu de l&apos;email</h2>
              <button
                onClick={() => setShowPreview(false)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-auto p-4">
              <div className="bg-gray-100 rounded-lg p-2 mb-4">
                <p className="text-sm">
                  <strong>Objet :</strong> {form.subject}
                </p>
              </div>
              <div
                className="email-preview"
                dangerouslySetInnerHTML={{ __html: form.htmlContent }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
