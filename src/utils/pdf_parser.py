"""
Utilitaire pour extraire le contenu des fichiers PDF (CV).
"""
import base64
import os
import tempfile
from pypdf import PdfReader
from typing import Optional


class PDFParser:
    """Classe pour parser les fichiers PDF."""
    
    @staticmethod
    def extract_text_from_base64(base64_content: str) -> str:
        """
        Extrait le texte d'un PDF encodé en base64.
        
        Args:
            base64_content: Le contenu du PDF encodé en base64.
            
        Returns:
            Le texte extrait du PDF.
        """
        try:
            # Décoder le contenu base64
            pdf_bytes = base64.b64decode(base64_content)
            
            # Créer un fichier temporaire pour stocker le PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(pdf_bytes)
                temp_file_path = temp_file.name
            
            # Extraire le texte du PDF
            text = PDFParser.extract_text_from_file(temp_file_path)
            
            # Supprimer le fichier temporaire
            os.unlink(temp_file_path)
            
            return text
        
        except Exception as e:
            raise Exception(f"Erreur lors de l'extraction du texte du PDF: {str(e)}")
    
    @staticmethod
    def extract_text_from_file(file_path: str) -> str:
        """
        Extrait le texte d'un fichier PDF.
        
        Args:
            file_path: Le chemin vers le fichier PDF.
            
        Returns:
            Le texte extrait du PDF.
        """
        try:
            # Ouvrir le PDF avec pypdf
            reader = PdfReader(file_path)
            
            # Extraire le texte de chaque page
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            return text
        
        except Exception as e:
            raise Exception(f"Erreur lors de l'extraction du texte du PDF: {str(e)}")
    
    @staticmethod
    def extract_text_from_uploaded_file(file_content: bytes, file_name: Optional[str] = None) -> str:
        """
        Extrait le texte d'un fichier PDF téléchargé.
        
        Args:
            file_content: Le contenu du fichier PDF.
            file_name: Optionnel, le nom du fichier.
            
        Returns:
            Le texte extrait du PDF.
        """
        try:
            # Créer un fichier temporaire pour stocker le PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            # Extraire le texte du PDF
            text = PDFParser.extract_text_from_file(temp_file_path)
            
            # Supprimer le fichier temporaire
            os.unlink(temp_file_path)
            
            return text
        
        except Exception as e:
            raise Exception(f"Erreur lors de l'extraction du texte du PDF: {str(e)}") 