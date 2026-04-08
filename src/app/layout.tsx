import type { Metadata } from "next";
import { Toaster } from "react-hot-toast";
import Sidebar from "@/components/sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "EmailPro - Plateforme d'Emailing",
  description: "Plateforme de gestion de campagnes d'email marketing",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body className="bg-gray-50 text-gray-900">
        <Toaster position="top-right" />
        <Sidebar />
        <main className="ml-[260px] min-h-screen transition-all duration-300">
          <div className="p-8">{children}</div>
        </main>
      </body>
    </html>
  );
}
