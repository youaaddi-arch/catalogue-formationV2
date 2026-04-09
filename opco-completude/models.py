"""Structures de données pour l'application OPCO EP."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PieceJustificative:
    """Représente une pièce justificative attendue ou trouvée."""
    id: str
    nom: str
    statut: str = "manquante"  # "trouvee", "manquante", "incertaine"
    fichier_nom: Optional[str] = None
    fichier_id: Optional[str] = None
    fichier_lien: Optional[str] = None
    score_match: float = 0.0
    source: Optional[str] = None  # "cible" ou "source"


@dataclass
class DonnéesExcel:
    """Données issues du fichier CONSTATS EP pour un apprenti."""
    numero_dossier: Optional[str] = None
    statut_dossier: Optional[str] = None
    csf: Optional[str] = None
    factures_assignation: Optional[str] = None
    controle_urssaf: Optional[str] = None
    rupture: Optional[str] = None
    date_rupture: Optional[str] = None
    maintien: Optional[str] = None
    date_fin_maintien: Optional[str] = None
    date_embauche: Optional[str] = None
    date_debut_formation: Optional[str] = None
    date_fin_formation: Optional[str] = None
    constats: list = field(default_factory=list)
    actions_cfa: Optional[str] = None


@dataclass
class Apprenti:
    """Représente un apprenti avec toutes ses informations."""
    nom: str
    nom_normalise: str = ""
    dossier_id: Optional[str] = None
    dossier_nom: Optional[str] = None
    dossier_source: Optional[str] = None  # "cible" ou "source"
    classe: Optional[str] = None
    jour_cours: Optional[str] = None  # lundi, mardi, etc.
    date_embauche: Optional[str] = None  # date début contrat entreprise
    date_debut_formation: Optional[str] = None
    date_fin_formation: Optional[str] = None
    pieces: list = field(default_factory=list)  # Liste de PieceJustificative
    donnees_excel: Optional[DonnéesExcel] = None
    score_completude: float = 0.0
    nb_pieces_trouvees: int = 0
    nb_pieces_attendues: int = 0

    def calculer_score(self):
        """Calcule le score de complétude."""
        if not self.pieces:
            return
        attendues = [p for p in self.pieces if p.statut != "non_applicable"]
        trouvees = [p for p in attendues if p.statut == "trouvee"]
        self.nb_pieces_attendues = len(attendues)
        self.nb_pieces_trouvees = len(trouvees)
        if self.nb_pieces_attendues > 0:
            self.score_completude = round(
                (self.nb_pieces_trouvees / self.nb_pieces_attendues) * 100, 1
            )
        else:
            self.score_completude = 100.0

    @property
    def est_complet(self) -> bool:
        return self.score_completude == 100.0

    @property
    def pieces_manquantes(self) -> list:
        return [p for p in self.pieces if p.statut == "manquante"]

    @property
    def pieces_trouvees(self) -> list:
        return [p for p in self.pieces if p.statut == "trouvee"]

    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour l'export."""
        result = {
            "Nom": self.nom,
            "Classe": self.classe or "",
            "Date d'embauche": self.date_embauche or "",
            "Jour de cours": self.jour_cours or "",
            "Début formation": self.date_debut_formation or "",
            "Fin formation": self.date_fin_formation or "",
            "Dossier Drive": self.dossier_nom or "Non trouvé",
            "Score": f"{self.score_completude}%",
            "Pièces trouvées": f"{self.nb_pieces_trouvees}/{self.nb_pieces_attendues}",
        }
        for p in self.pieces:
            if p.statut == "non_applicable":
                result[p.nom] = "N/A"
            elif p.statut == "trouvee":
                result[p.nom] = "✅"
            elif p.statut == "incertaine":
                result[p.nom] = "⚠️"
            else:
                result[p.nom] = "❌"
        if self.donnees_excel:
            result["N° Dossier"] = self.donnees_excel.numero_dossier or ""
            result["Statut dossier"] = self.donnees_excel.statut_dossier or ""
            result["Actions CFA"] = self.donnees_excel.actions_cfa or ""
        return result
