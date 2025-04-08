"""
Agent d'analyse de CV basé sur LangChain.
Extrait les informations pertinentes d'un CV: poste recherché, compétences,
expérience professionnelle et cursus académique.
"""
import os
import json
from typing import Dict, Any, List, Optional
import base64

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field, validator

from src.models.cv import CVData, Education, Experience, Project
from src.utils.pdf_parser import PDFParser


class CVAnalyzerAgent:
    """Agent d'analyse de CV basé sur LangChain."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise l'agent d'analyse de CV.
        
        Args:
            api_key: Clé API OpenAI, par défaut utilise la variable d'environnement.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("Clé API OpenAI non configurée.")
        
        # Initialisation du modèle de langage
        self.llm = ChatOpenAI(
            api_key=self.api_key,
            model="gpt-4o",
            temperature=0.2
        )
        
        # Construction du prompt d'extraction des informations du CV
        self.cv_extraction_prompt = ChatPromptTemplate.from_template("""
        Tu es un expert en analyse de CV. Analyse ce CV et extrait les informations suivantes:
        
        1. Le poste recherché par le candidat, précisément et sans ajout de votre part
        2. Le type de contrat recherché (CDI, CDD, Stage, Alternance, Intérim, Freelance, etc.)
        3. Ses compétences techniques et non techniques
        4. Ses expériences professionnelles (avec dates, entreprises, postes, descriptions)
        5. Son cursus académique (avec dates, institutions, diplômes, domaines d'étude)
        6. Ses projets personnels et académiques (avec dates, titres, descriptions, technologies utilisées)
        
        CV à analyser:
        ```
        {cv_text}
        ```
        
        Important concernant le poste recherché et le type de contrat:
        - N'invente pas de poste si ce n'est pas clairement mentionné dans le CV
        - Sépare clairement le titre du poste et le type de contrat
        - Si le poste mentionné contient des termes comme "Stage", "Alternance", etc., place ces informations dans le champ "desired_contract"
        - Le champ "desired_job" ne doit contenir QUE le titre du poste sans mention du type de contrat ou niveau d'expérience
        
        Réponds STRICTEMENT au format JSON suivant:
        
        ```json
        {{
            "full_name": "Nom complet du candidat",
            "email": "Adresse email (si disponible)",
            "phone": "Numéro de téléphone (si disponible)",
            "location": "Localisation géographique (si disponible)",
            "desired_job": "Poste recherché (TITRE UNIQUEMENT, sans mention de stage/alternance/etc.)",
            "desired_contract": "Type de contrat recherché (CDI, CDD, Stage, Alternance, etc.)",
            "skills": ["compétence1", "compétence2", ...],
            "projects": [
                {{
                    "title": "Titre du projet",
                    "start_date": "YYYY-MM",
                    "end_date": "YYYY-MM",
                    "description": "Description du projet",
                    "technologies": ["techno1", "techno2", ...]
                }},
                ...
            ],
            "experiences": [
                {{
                    "company": "Nom de l'entreprise",
                    "position": "Poste occupé",
                    "start_date": "YYYY-MM",
                    "end_date": "YYYY-MM ou 'present'",
                    "location": "Lieu de travail (si disponible)",
                    "description": "Description des responsabilités"
                }},
                ...
            ],
            "education": [
                {{
                    "institution": "Nom de l'établissement",
                    "diploma": "Diplôme obtenu",
                    "field_of_study": "Domaine d'étude",
                    "start_date": "YYYY-MM",
                    "end_date": "YYYY-MM",
                    "description": "Description de la formation (si disponible)"
                }},
                ...
            ],
            "languages": ["langue1", "langue2", ...],
            "summary": "Résumé du profil (si disponible)"
        }}
        ```
        
        Si une information n'est pas disponible, laisse le champ correspondant vide ou null.
        Pour les dates, utilise le format YYYY-MM (ex: 2021-06). Si seule l'année est disponible, utilise YYYY-01.
        """)
        
        # Construction de la chaîne d'extraction
        self.extraction_chain = (
            self.cv_extraction_prompt 
            | self.llm 
            | StrOutputParser() 
            | self._parse_json_response
        )
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """
        Parse la réponse JSON du LLM.
        
        Args:
            text: Réponse textuelle du LLM.
            
        Returns:
            Dictionnaire contenant les données extraites du CV.
        """
        # Nettoyer la réponse pour extraire uniquement le JSON
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        
        if json_start == -1 or json_end == 0:
            raise ValueError("Réponse invalide: pas de JSON trouvé")
        
        json_str = text[json_start:json_end]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Erreur de parsing JSON: {str(e)}")
    
    def extract_from_text(self, cv_text: str) -> CVData:
        """
        Extrait les informations d'un CV à partir de son texte.
        
        Args:
            cv_text: Texte du CV.
            
        Returns:
            Objet CVData contenant les informations extraites.
        """
        # Extraire les informations du CV
        extracted_data = self.extraction_chain.invoke({"cv_text": cv_text})
        
        # Convertir les expériences professionnelles
        experiences = [
            Experience(**exp) for exp in extracted_data.get("experiences", [])
        ]
        
        # Convertir le cursus académique
        education = [
            Education(**edu) for edu in extracted_data.get("education", [])
        ]
        
        # Convertir les projets
        projects = None
        if "projects" in extracted_data and extracted_data["projects"]:
            projects = [
                Project(**proj) for proj in extracted_data.get("projects", [])
            ]
        
        # Analyser le poste recherché pour séparer le titre du poste et le type de contrat
        desired_job = extracted_data.get("desired_job", "Non spécifié")
        desired_contract = extracted_data.get("desired_contract")
        
        # Si le LLM n'a pas identifié de type de contrat, analyser le titre du poste
        # pour tenter d'en extraire un
        if not desired_contract:
            # Listes des mots-clés indiquant des types de contrat
            contract_keywords = {
                "Stage": "STG",
                "Alternance": "ALT",
                "Apprentissage": "ALT",
                "Apprenti": "ALT",
                "CDD": "CDD",
                "CDI": "CDI",
                "Intérim": "MIS",
                "Interim": "MIS",
                "Freelance": "LIB",
                "Indépendant": "LIB",
                "Saisonnier": "SAI",
                "Junior": None,  # Junior n'est pas un type de contrat, mais un niveau d'expérience
                "Senior": None,  # Senior n'est pas un type de contrat, mais un niveau d'expérience
            }
            
            # Mots à ignorer dans le titre du poste
            ignore_keywords = ["technique", "junior", "senior", "confirmé", "débutant"]
            
            # Vérifier si le poste contient un type de contrat
            job_parts = desired_job.split()
            cleaned_job_parts = []
            
            for part in job_parts:
                part_lower = part.lower()
                contract_found = False
                
                # Vérifier si le mot est un type de contrat
                for keyword, code in contract_keywords.items():
                    if keyword.lower() in part_lower:
                        if code and not desired_contract:  # Ne prendre que le premier type de contrat trouvé
                            desired_contract = code
                        contract_found = True
                        break
                
                # Vérifier si le mot doit être ignoré
                ignore_word = False
                for keyword in ignore_keywords:
                    if keyword.lower() in part_lower:
                        ignore_word = True
                        break
                
                # Ajouter le mot au titre nettoyé s'il n'est ni un type de contrat ni un mot à ignorer
                if not contract_found and not ignore_word:
                    cleaned_job_parts.append(part)
            
            # Reconstruire le titre du poste nettoyé
            cleaned_job_title = " ".join(cleaned_job_parts).strip()
            if cleaned_job_title:
                desired_job = cleaned_job_title
        
        # Créer l'objet CVData
        cv_data = CVData(
            full_name=extracted_data.get("full_name", ""),
            email=extracted_data.get("email"),
            phone=extracted_data.get("phone"),
            location=extracted_data.get("location"),
            desired_job=desired_job,
            desired_contract=desired_contract,
            skills=extracted_data.get("skills", []),
            experiences=experiences,
            projects=projects,
            education=education,
            languages=extracted_data.get("languages"),
            summary=extracted_data.get("summary")
        )
        
        return cv_data
    
    def extract_from_pdf(self, pdf_content: str) -> CVData:
        """
        Extrait les informations d'un CV à partir d'un contenu PDF en base64.
        
        Args:
            pdf_content: Contenu du PDF encodé en base64.
            
        Returns:
            Objet CVData contenant les informations extraites.
        """
        # Extraire le texte du PDF
        cv_text = PDFParser.extract_text_from_base64(pdf_content)
        
        # Extraire les informations du CV
        return self.extract_from_text(cv_text)
    
    def extract_from_file(self, file_path: str) -> CVData:
        """
        Extrait les informations d'un CV à partir d'un fichier PDF.
        
        Args:
            file_path: Chemin vers le fichier PDF.
            
        Returns:
            Objet CVData contenant les informations extraites.
        """
        # Extraire le texte du PDF
        cv_text = PDFParser.extract_text_from_file(file_path)
        
        # Extraire les informations du CV
        return self.extract_from_text(cv_text) 