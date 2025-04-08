"""
Agent de recherche d'emploi basé sur LangChain.
Utilise les APIs de France Travail, LinkedIn, Indeed et Glassdoor pour trouver 
des offres d'emploi correspondant au profil de l'utilisateur.
"""
import os
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain_core.output_parsers import StrOutputParser

from src.models.job import (
    JobPosting, JobSource, JobSearchRequest, JobSearchResponse, Location
)
from src.models.cv import CVData
from src.utils.api_clients import (
    FranceTravailClient, LinkedInClient, IndeedClient, GlassdoorClient
)


class JobSearcherAgent:
    """Agent de recherche d'emploi basé sur LangChain."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise l'agent de recherche d'emploi.
        
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
        
        # Initialisation des clients API
        self.clients = {
            JobSource.FRANCE_TRAVAIL: self._init_client(FranceTravailClient),
            # Sources temporairement désactivées (pas de suppression de code)
            JobSource.LINKEDIN: None,  # self._init_client(LinkedInClient),
            JobSource.INDEED: None,    # self._init_client(IndeedClient),
            JobSource.GLASSDOOR: None, # self._init_client(GlassdoorClient)
        }
        
        # Construction du prompt d'enrichissement de requête
        self.query_enrichment_prompt = ChatPromptTemplate.from_template("""
        Tu es un expert en recherche d'emploi. Je te donne des informations sur un profil de candidat et un poste recherché.
        Ton objectif est d'enrichir la requête de recherche d'emploi avec des mots-clés pertinents pour maximiser les chances de trouver des offres correspondant au profil.
        
        Profil du candidat:
        ```
        {cv_data}
        ```
        
        Poste recherché: {job_title}
        Localisation: {location}
        
        Génère 5 à 10 mots-clés ou compétences pertinents pour cette recherche, en tenant compte du profil du candidat.
        Réponds UNIQUEMENT avec une liste de mots-clés séparés par des virgules, sans introduction ni commentaire.
        """)
        
        # Construction de la chaîne d'enrichissement
        self.enrichment_chain = (
            self.query_enrichment_prompt 
            | self.llm 
            | StrOutputParser()
        )
    
    def _init_client(self, client_class):
        """
        Initialise un client API si possible, sinon renvoie None.
        
        Args:
            client_class: Classe du client à initialiser.
            
        Returns:
            Instance du client ou None en cas d'erreur.
        """
        try:
            return client_class()
        except ValueError:
            return None
    
    def enrich_search_query(self, job_title: str, location: str, cv_data: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Enrichit une requête de recherche avec des mots-clés pertinents.
        
        Args:
            job_title: Titre du poste recherché.
            location: Localisation (ville, région, pays).
            cv_data: Données du CV pour affiner la recherche.
            
        Returns:
            Liste de mots-clés pertinents.
        """
        if not cv_data:
            return []
        
        # Convertir cv_data en format lisible
        cv_text = f"""
        Poste recherché: {cv_data.get('desired_job', '')}
        Compétences: {', '.join(cv_data.get('skills', []))}
        Expériences: {', '.join([f"{e.get('position', '')} chez {e.get('company', '')}" for e in cv_data.get('experiences', [])])}
        Formation: {', '.join([f"{e.get('diploma', '')} en {e.get('field_of_study', '')}" for e in cv_data.get('education', [])])}
        """
        
        # Invoquer la chaîne d'enrichissement
        keywords_str = self.enrichment_chain.invoke({
            "cv_data": cv_text,
            "job_title": job_title,
            "location": location
        })
        
        # Convertir la chaîne en liste
        keywords = [kw.strip() for kw in keywords_str.split(",")]
        
        return keywords
    
    def search_jobs(self, query: JobSearchRequest) -> JobSearchResponse:
        """
        Recherche des offres d'emploi correspondant aux critères spécifiés.
        
        Args:
            query: Critères de recherche.
            
        Returns:
            Résultats de la recherche.
        """
        # Si des données CV sont fournies, enrichir la requête
        enriched_query = query
        
        # Déterminer les sources disponibles
        available_sources = [source for source, client in self.clients.items() if client is not None]
        if not available_sources:
            raise ValueError("Aucune source d'emploi n'est disponible. Veuillez configurer au moins une source.")
        
        # Recherche sur toutes les sources disponibles en parallèle
        results = []
        failed_sources = []
        
        with ThreadPoolExecutor(max_workers=len(available_sources)) as executor:
            # Lancer les recherches en parallèle
            future_to_source = {
                executor.submit(self._search_on_source, source, query): source
                for source in available_sources
            }
            
            # Récupérer les résultats et gérer les erreurs
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    source_results = future.result()
                    
                    # Convertir les dictionnaires bruts en objets JobPosting
                    if source == JobSource.FRANCE_TRAVAIL:
                        processed_results = self._process_france_travail_results(source_results)
                    else:
                        processed_results = source_results
                    
                    results.extend(processed_results)
                except Exception as e:
                    print(f"Erreur lors de la recherche sur {source}: {str(e)}")
                    failed_sources.append(source)
        
        # Trier les résultats par date de publication (du plus récent au plus ancien)
        try:
            results.sort(key=lambda job: job.posted_date if hasattr(job, 'posted_date') and job.posted_date else "", reverse=True)
        except Exception as e:
            print(f"Erreur lors du tri des résultats: {str(e)}")
            # Continuer sans tri en cas d'erreur
        
        # Construire et retourner la réponse
        response = JobSearchResponse(
            query=enriched_query,
            results=results,
            available_sources=[source.value for source in available_sources],
            failed_sources=[source.value for source in failed_sources],
            total_count=len(results)
        )
        
        return response
    
    def _search_on_source(self, source: JobSource, query: JobSearchRequest) -> List[JobPosting]:
        """
        Recherche des offres d'emploi sur une source spécifique.
        
        Args:
            source: Source d'emploi.
            query: Critères de recherche.
            
        Returns:
            Liste des offres d'emploi trouvées.
        """
        client = self.clients.get(source)
        if not client:
            raise ValueError(f"Client non configuré pour la source {source.value}")
        
        try:
            return client.search_jobs(
                job_title=query.job_title,
                location=query.location,
                radius=query.radius,
                keywords=query.keywords,
                limit=query.limit_per_source
            )
        except Exception as e:
            print(f"Erreur lors de la recherche sur {source.value}: {str(e)}")
            raise
    
    def _process_france_travail_results(self, results: List[Dict[str, Any]]) -> List[JobPosting]:
        """
        Convertit les résultats bruts de France Travail en objets JobPosting.
        
        Args:
            results: Liste des résultats bruts de l'API France Travail.
            
        Returns:
            Liste d'objets JobPosting.
        """
        job_postings = []
        
        for job in results:
            try:
                # Extraction des informations pertinentes
                job_id = job.get("id", "")
                title = job.get("intitule", "")
                company = job.get("entreprise", {}).get("nom", "Non spécifié")
                description = job.get("description", "")
                url = job.get("origineOffre", {}).get("urlOrigine", "https://www.francetravail.fr/")
                posted_date = job.get("dateCreation", "")
                
                # Extraction de la localisation
                location_data = job.get("lieuTravail", {})
                city = location_data.get("libelle", "")
                postal_code = location_data.get("codePostal", "")
                country = "France"
                
                # Création de l'objet Location
                location = Location(
                    city=city,
                    postal_code=postal_code,
                    region="",
                    country=country,
                    formatted_address=f"{city}, {postal_code}, {country}"
                )
                
                # Extraction des compétences requises
                skills = []
                if "competences" in job:
                    skills = [comp.get("libelle", "") for comp in job.get("competences", [])]
                
                # Extraction du type de contrat et du salaire
                contract_type = job.get("typeContrat", "")
                salary = job.get("salaire", {}).get("libelle", "")
                
                # Création de l'objet JobPosting
                job_posting = JobPosting(
                    job_id=job_id,
                    title=title,
                    company=company,
                    location=location,
                    description=description,
                    url=url,
                    posted_date=posted_date,
                    salary_range=salary,
                    job_type=contract_type,
                    required_skills=skills,
                    required_experience=job.get("experienceExige", ""),
                    required_education=job.get("formationExige", ""),
                    source=JobSource.FRANCE_TRAVAIL,
                    raw_data=job
                )
                
                job_postings.append(job_posting)
            except Exception as e:
                print(f"Erreur lors du traitement d'une offre France Travail: {str(e)}")
                # Continuer avec l'offre suivante
        
        return job_postings 