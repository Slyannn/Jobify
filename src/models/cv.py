"""
Modèles de données pour les CV et les informations extraites.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class Education(BaseModel):
    """Modèle pour une formation académique."""
    institution: str = Field(..., description="Nom de l'établissement")
    diploma: str = Field(..., description="Diplôme obtenu")
    field_of_study: Optional[str] = Field(None, description="Domaine d'étude")
    start_date: str = Field(..., description="Date de début (format: YYYY-MM)")
    end_date: Optional[str] = Field(None, description="Date de fin (format: YYYY-MM)")
    description: Optional[str] = Field(None, description="Description de la formation")


class Experience(BaseModel):
    """Modèle pour une expérience professionnelle."""
    company: str = Field(..., description="Nom de l'entreprise")
    position: str = Field(..., description="Poste occupé")
    start_date: str = Field(..., description="Date de début (format: YYYY-MM)")
    end_date: Optional[str] = Field(None, description="Date de fin (format: YYYY-MM)")
    location: Optional[str] = Field(None, description="Lieu de travail")
    description: Optional[str] = Field(None, description="Description des responsabilités")


class Project(BaseModel):
    """Modèle pour un projet personnel ou académique."""
    title: str = Field(..., description="Titre du projet")
    start_date: Optional[str] = Field(None, description="Date de début (format: YYYY-MM)")
    end_date: Optional[str] = Field(None, description="Date de fin (format: YYYY-MM)")
    description: Optional[str] = Field(None, description="Description du projet")
    technologies: Optional[List[str]] = Field(None, description="Technologies utilisées")
    url: Optional[str] = Field(None, description="URL du projet (GitHub, site web, etc.)")


class CVData(BaseModel):
    """Modèle pour les données extraites d'un CV."""
    full_name: str = Field(..., description="Nom complet")
    email: Optional[str] = Field(None, description="Adresse email")
    phone: Optional[str] = Field(None, description="Numéro de téléphone")
    location: Optional[str] = Field(None, description="Localisation géographique")
    desired_job: str = Field(..., description="Poste recherché")
    desired_contract: Optional[str] = Field(None, description="Type de contrat recherché (CDI, CDD, Stage, Alternance, etc.)")
    skills: List[str] = Field(..., description="Liste des compétences")
    experiences: List[Experience] = Field(..., description="Expériences professionnelles")
    projects: Optional[List[Project]] = Field(None, description="Projets personnels ou académiques")
    education: List[Education] = Field(..., description="Formations académiques")
    languages: Optional[List[str]] = Field(None, description="Langues maîtrisées")
    summary: Optional[str] = Field(None, description="Résumé du profil")


class CVUpload(BaseModel):
    """Modèle pour le téléchargement d'un CV."""
    file_content: str = Field(..., description="Contenu du fichier encodé en base64")
    file_type: str = Field(..., description="Type de fichier (pdf, docx)")


class CVAnalysisRequest(BaseModel):
    """Modèle pour une demande d'analyse de CV."""
    cv_data: Optional[CVData] = Field(None, description="Données de CV (si déjà extraites)")
    cv_upload: Optional[CVUpload] = Field(None, description="Fichier CV à analyser")

    class Config:
        schema_extra = {
            "example": {
                "cv_upload": {
                    "file_content": "base64_encoded_content",
                    "file_type": "pdf"
                }
            }
        } 