"""
Clients API pour les plateformes de recherche d'emploi.
"""
import os
import json
import requests
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from src.models.job import JobPosting, Location, JobSource

# Charger les variables d'environnement
load_dotenv()


class JobAPIClient(ABC):
    """Classe abstraite pour les clients API de recherche d'emploi."""
    
    @abstractmethod
    def search_jobs(self, job_title: str, location: Optional[str] = None, 
                   radius: int = 50, keywords: Optional[List[str]] = None, 
                   limit: int = 10) -> List[JobPosting]:
        """
        Recherche des offres d'emploi.
        
        Args:
            job_title: Le titre du poste recherché.
            location: Optionnel, la localisation (ville, région, pays).
            radius: Le rayon de recherche en km.
            keywords: Optionnel, des mots-clés supplémentaires.
            limit: Le nombre maximum de résultats à retourner.
            
        Returns:
            Une liste d'offres d'emploi.
        """
        pass


class FranceTravailClient(JobAPIClient):
    """Client API pour France Travail (anciennement Pôle Emploi)."""
    
    def __init__(self):
        """Initialise le client France Travail avec la clé API ou OAuth2."""
        # Vérifier d'abord les identifiants OAuth2
        self.client_id = os.getenv("FRANCE_TRAVAIL_CLIENT_ID")
        self.client_secret = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET")
        self.api_key = os.getenv("FRANCE_TRAVAIL_API_KEY")
        
        # URL de base de l'API - Mise à jour vers la nouvelle URL
        self.api_base_url = "https://api.francetravail.io/partenaire/offresdemploi/v2"
        
        # Aucune information d'authentification disponible
        if not self.client_id and not self.client_secret and not self.api_key:
            print("AVERTISSEMENT: Aucune information d'authentification France Travail configurée.")
            print("Pour utiliser l'API France Travail:")
            print("1. Inscrivez-vous sur https://francetravail.io/catalogue/offres-emploi")
            print("2. Créez un compte développeur et une application")
            print("3. Obtenez client_id et client_secret")
            print("4. Créez un fichier .env à la racine du projet avec:")
            print("   FRANCE_TRAVAIL_CLIENT_ID=votre_client_id")
            print("   FRANCE_TRAVAIL_CLIENT_SECRET=votre_client_secret")
            print("OU si vous avez déjà un token d'accès:")
            print("   FRANCE_TRAVAIL_API_KEY=votre_clé_api")
        
        # Stocker le token d'accès avec sa date d'expiration
        self.access_token = None
        self.token_expiry = None

    def _get_access_token(self):
        """
        Obtient un token d'accès via OAuth2.
        
        Returns:
            Le token d'accès ou None en cas d'échec.
        """
        if not self.client_id or not self.client_secret:
            return None
            
        # URL pour l'authentification OAuth2 avec le paramètre realm
        token_url = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
        
        # Paramètres pour la requête de token selon la documentation officielle
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "api_offresdemploiv2 o2dsoffre"
        }
        
        # Headers pour la requête
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            # Requête pour obtenir le token
            response = requests.post(token_url, data=data, headers=headers)
            
            if response.status_code != 200:
                print(f"Erreur d'authentification France Travail: {response.status_code} - {response.text}")
                return None
            
            # Extraire le token de la réponse
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                print("Aucun token d'accès dans la réponse France Travail")
                return None
            
            # Mettre à jour le token et sa durée de validité
            self.access_token = access_token
            # Enregistrer l'expiration si disponible dans la réponse
            if "expires_in" in token_data:
                from datetime import datetime, timedelta
                self.token_expiry = datetime.now() + timedelta(seconds=token_data["expires_in"])
            
            return access_token
            
        except Exception as e:
            print(f"Erreur lors de l'obtention du token France Travail: {str(e)}")
            return None
    
    def _get_auth_token(self):
        """
        Récupère un token d'authentification valide.
        
        Returns:
            Un token d'authentification valide ou None en cas d'échec.
        """
        # Utiliser l'API key si disponible
        if self.api_key:
            return self.api_key
            
        # Vérifier si le token est expiré
        if self.access_token and self.token_expiry:
            from datetime import datetime
            if datetime.now() < self.token_expiry:
                return self.access_token
        
        # Obtenir un nouveau token
        return self._get_access_token()
        
    def search_jobs(self, job_title: str, location: str, radius: int = 50, keywords: Optional[List[str]] = None, 
                  limit: int = 10, contract_type: Optional[str] = None, job_keywords: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Recherche des offres d'emploi via l'API France Travail.
        
        Args:
            job_title: Titre du poste recherché (peut contenir des indications sur le type de contrat).
            location: Localisation (ville, département, code postal, ou adresse complète).
            radius: Le rayon de recherche en km (utilisé uniquement si le format de localisation le permet).
            keywords: Optionnel, des mots-clés supplémentaires.
            limit: Le nombre maximum de résultats à retourner.
            contract_type: Optionnel, le type de contrat déjà prétraité par le LLM (STG, ALT, CDD, CDI, etc.)
            job_keywords: Optionnel, les mots-clés du poste déjà extraits par le LLM.
            
        Returns:
            Une liste d'offres d'emploi sous forme de dictionnaires.
        """
        # Obtenir un token d'authentification
        auth_token = self._get_auth_token()
        
        # Vérifiez si le token est disponible
        if not auth_token:
            raise ValueError("Authentification France Travail non configurée. Impossible d'effectuer la recherche.")
        
        # Utiliser soit les mots-clés fournis par le LLM, soit analyser le job_title
        if job_keywords:
            # Utiliser directement les mots-clés prétraités par le LLM
            motsCles = job_keywords
            print(f"Utilisation des mots-clés prétraités par le LLM: {motsCles}")
        else:
            # Comportement existant: analyser le job_title pour détecter les types de contrat
            job_title_clean = job_title
            detected_contract_type = None
            
            # Listes des mots-clés indiquant des types de contrat
            contract_keywords = {
                "Stage": "STG",            # Stage
                "Alternance": "ALT",       # Alternance / Apprentissage / Professionnalisation
                "CDD": "CDD",              # Contrat à durée déterminée
                "CDI": "CDI",              # Contrat à durée indéterminée
                "Intérim": "MIS",          # Mission intérimaire
                "Freelance": "LIB",        # Profession libérale
                "Saisonnier": "SAI"        # Contrat travail saisonnier
            }
            
            # Vérifier si l'intitulé contient un type de contrat
            for keyword, code in contract_keywords.items():
                if keyword.lower() in job_title.lower():
                    detected_contract_type = code
                    # Retirer le mot-clé du type de contrat de l'intitulé
                    job_title_clean = job_title.lower().replace(keyword.lower(), "").strip()
                    print(f"Type de contrat détecté: {keyword} (code API: {code})")
                    print(f"Intitulé du poste nettoyé: {job_title_clean}")
                    break
            
            # Cas spécial pour "technique", qui n'est pas un mot utile pour la recherche
            job_title_clean = job_title_clean.replace("technique", "").strip()
            motsCles = job_title_clean
            print(f"***********Mots-clés pour la recherche: {motsCles}***********")
            
            # Utiliser le type de contrat détecté si aucun n'a été fourni explicitement
            if not contract_type and detected_contract_type:
                contract_type = detected_contract_type
                print(f"Type de contrat détecté et stocké: {contract_type}")
        
        # Construction des paramètres de recherche
        params = {
            "motsCles": motsCles,
            "range": f"0-{limit-1}"
        }
        
        # Commenté: Ne pas utiliser le type de contrat pour le moment car l'API ne retourne pas correctement les résultats
        # if contract_type:
        #     params["typeContrat"] = contract_type
        #     print(f"Type de contrat utilisé pour la recherche: {contract_type}")
        
        # Ajouter la localisation en utilisant le paramètre departement
        if location:
            # Extraire le code postal et le département
            import re
            
            # Essayer d'extraire un code postal à 5 chiffres de l'adresse
            postal_code_match = re.search(r'(?<!\d)(\d{5})(?!\d)', location)
            if postal_code_match:
                # Utiliser les 2 premiers chiffres du code postal comme code département
                dept_code = postal_code_match.group(1)[:2]
                params["departement"] = dept_code
                print(f"Recherche dans le département {dept_code} (extrait du code postal)")
            
            # Si c'est déjà un code de département à 2 chiffres, l'utiliser directement
            elif len(location) == 2 and location.isdigit():
                params["departement"] = location
                print(f"Recherche dans le département {location}")
            
            # Si c'est un nom de département ou ville bien connu
            elif location.lower() in ["paris", "lyon", "marseille", "toulouse", "nice", "bordeaux", "lille"]:
                # Mapping simplifié des grandes villes
                dept_codes = {
                    "paris": "75",
                    "lyon": "69",
                    "marseille": "13",
                    "toulouse": "31",
                    "nice": "06",
                    "bordeaux": "33",
                    "lille": "59"
                }
                params["departement"] = dept_codes[location.lower()]
                print(f"Recherche dans le département {params['departement']} ({location})")
            
            # Valeur par défaut si aucun format reconnu
            else:
                # Utiliser Paris par défaut
                params["departement"] = "75"
                print(f"Format de localisation non reconnu: '{location}'. Utilisation du département 75 (Paris) par défaut.")
        
        # Ajouter les mots-clés supplémentaires
        # Commenté: Ne pas ajouter les compétences du CV aux mots-clés de recherche
        # car cela rend les résultats trop spécifiques et modifie la requête initiale
        if keywords:
            print(f"INFO: {len(keywords)} compétences disponibles mais non ajoutées à la requête")
            print(f"Les compétences suivantes ne sont pas incluses dans la recherche: {', '.join(keywords[:5])}...")
            # Ancienne logique qui ajoutait les compétences aux mots-clés:
            # original_keywords = params["motsCles"]
            # skills_keywords = ' '.join(keywords)
            # params["motsCles"] = f"{original_keywords} {skills_keywords}"
        
        # Construction des en-têtes avec l'authentification
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Accept": "application/json"
        }
        
        try:
            # Requête à l'API
            print("=== REQUÊTE API FRANCE TRAVAIL ===")
            print(f"URL: {self.api_base_url}/offres/search")
            print(f"Paramètres: {json.dumps(params, indent=2, ensure_ascii=False)}")
            print("================================")
            
            response = requests.get(f"{self.api_base_url}/offres/search", params=params, headers=headers)
            print(f"URL demandée: {response.url}")
            
            # Vérification de la réponse
            if response.status_code == 401:
                # Essayer de renouveler le token si possible
                if self.client_id and self.client_secret and self.access_token:
                    print("Token expiré, tentative de renouvellement...")
                    self.access_token = None  # Forcer la récupération d'un nouveau token
                    new_token = self._get_auth_token()
                    if new_token:
                        headers["Authorization"] = f"Bearer {new_token}"
                        response = requests.get(f"{self.api_base_url}/offres/search", params=params, headers=headers)
                        if response.status_code in [200, 206]:
                            print("Requête réussie avec le nouveau token.")
                        else:
                            raise ValueError(f"Erreur d'authentification avec l'API France Travail: Clé API invalide (code 401)")
                else:
                    raise ValueError(f"Erreur d'authentification avec l'API France Travail: Clé API invalide (code 401)")
            
            # Le code 206 (Partial Content) est valide pour les réponses paginées
            if response.status_code not in [200, 206]:
                raise ValueError(f"Erreur lors de la recherche sur France Travail: {response.status_code} - {response.text}")
            
            # Traitement de la réponse
            data = response.json()
            
            # Vérifier la structure des résultats
            if "resultats" in data:
                # La structure peut varier selon la version de l'API
                if isinstance(data["resultats"], dict):
                    results = data["resultats"].get("resultats", [])
                else:
                    results = data["resultats"]
            else:
                results = []
            
            # Retourner directement les résultats bruts
            return results
        
        except requests.RequestException as e:
            raise ValueError(f"Erreur lors de la recherche sur France Travail: {str(e)}")
        except Exception as e:
            raise ValueError(f"Erreur lors du traitement des résultats France Travail: {str(e)}")


class LinkedInClient(JobAPIClient):
    """Client pour LinkedIn (utilisant Playwright pour le scraping)."""
    
    def __init__(self):
        """Initialise le client avec les identifiants LinkedIn."""
        self.username = os.getenv("LINKEDIN_USERNAME")
        self.password = os.getenv("LINKEDIN_PASSWORD")
        if not self.username or not self.password:
            raise ValueError("Les identifiants LinkedIn ne sont pas configurés.")
    
    def search_jobs(self, job_title: str, location: Optional[str] = None, 
                   radius: int = 50, keywords: Optional[List[str]] = None, 
                   limit: int = 10) -> List[JobPosting]:
        """
        Recherche des offres d'emploi sur LinkedIn.
        
        Args:
            job_title: Le titre du poste recherché.
            location: Optionnel, la localisation (ville, région, pays).
            radius: Le rayon de recherche en km.
            keywords: Optionnel, des mots-clés supplémentaires.
            limit: Le nombre maximum de résultats à retourner.
            
        Returns:
            Une liste d'offres d'emploi.
        """
        results = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            # Se connecter à LinkedIn
            page.goto("https://www.linkedin.com/login")
            page.fill("input#username", self.username)
            page.fill("input#password", self.password)
            page.click("button[type='submit']")
            page.wait_for_navigation()
            
            # Construire l'URL de recherche
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={job_title}"
            if location:
                search_url += f"&location={location}"
            if keywords:
                search_url += f"&{'+'.join(keywords)}"
            
            # Accéder à la page de recherche
            page.goto(search_url)
            page.wait_for_selector(".jobs-search__results-list")
            
            # Extraire les offres d'emploi
            job_cards = page.query_selector_all(".jobs-search__results-list > li")
            job_count = 0
            
            for card in job_cards:
                if job_count >= limit:
                    break
                
                # Extraire les informations de base
                title_element = card.query_selector(".base-search-card__title")
                company_element = card.query_selector(".base-search-card__subtitle")
                location_element = card.query_selector(".job-search-card__location")
                date_element = card.query_selector(".job-search-card__listdate")
                
                if not title_element or not company_element or not location_element:
                    continue
                
                title = title_element.inner_text().strip()
                company = company_element.inner_text().strip()
                location_str = location_element.inner_text().strip()
                posted_date = date_element.get_attribute("datetime") if date_element else datetime.now().strftime("%Y-%m-%d")
                
                # Cliquer sur la carte pour voir les détails
                card.click()
                page.wait_for_selector(".jobs-description-content")
                
                # Extraire les détails de l'offre
                description = page.query_selector(".jobs-description-content").inner_text()
                job_url = page.url
                
                # Extraire la ville et le pays de la localisation
                city = location_str.split(",")[0].strip() if "," in location_str else location_str
                country = location_str.split(",")[-1].strip() if "," in location_str else "France"
                
                # Créer l'objet Location
                location_obj = Location(
                    city=city,
                    postal_code=None,
                    region=None,
                    country=country,
                    formatted_address=location_str
                )
                
                # Créer l'objet JobPosting
                job_id = f"linkedin_{job_count}"
                job_posting = JobPosting(
                    job_id=job_id,
                    title=title,
                    company=company,
                    location=location_obj,
                    description=description,
                    url=job_url,
                    posted_date=posted_date,
                    salary_range=None,
                    job_type=None,
                    required_skills=None,
                    required_experience=None,
                    required_education=None,
                    source=JobSource.LINKEDIN,
                    raw_data={
                        "title": title,
                        "company": company,
                        "location": location_str,
                        "description": description,
                        "url": job_url
                    }
                )
                
                results.append(job_posting)
                job_count += 1
            
            # Fermer le navigateur
            browser.close()
        
        return results


class IndeedClient(JobAPIClient):
    """Client pour l'API Indeed."""
    
    def __init__(self):
        """Initialise le client avec la clé API."""
        self.api_key = os.getenv("INDEED_API_KEY")
        self.base_url = "https://api.indeed.com/ads/apisearch"
        if not self.api_key:
            raise ValueError("La clé API Indeed n'est pas configurée.")
    
    def search_jobs(self, job_title: str, location: Optional[str] = None, 
                   radius: int = 50, keywords: Optional[List[str]] = None, 
                   limit: int = 10) -> List[JobPosting]:
        """
        Recherche des offres d'emploi sur Indeed.
        
        Args:
            job_title: Le titre du poste recherché.
            location: Optionnel, la localisation (ville, région, pays).
            radius: Le rayon de recherche en km.
            keywords: Optionnel, des mots-clés supplémentaires.
            limit: Le nombre maximum de résultats à retourner.
            
        Returns:
            Une liste d'offres d'emploi.
        """
        # Construire les paramètres de recherche
        params = {
            "publisher": self.api_key,
            "q": job_title,
            "limit": limit,
            "radius": radius,
            "format": "json",
            "v": "2"
        }
        
        # Ajouter la localisation si spécifiée
        if location:
            params["l"] = location
        
        # Informer que les mots-clés supplémentaires sont disponibles mais non utilisés
        if keywords:
            print(f"INFO: {len(keywords)} compétences disponibles mais non ajoutées à la requête Indeed")
            print(f"Les compétences suivantes ne sont pas incluses dans la recherche Indeed: {', '.join(keywords[:5])}...")
            # Ancienne logique qui ajoutait les compétences aux mots-clés:
            # params["q"] += " " + " ".join(keywords)
        
        # Effectuer la requête
        response = requests.get(
            self.base_url,
            params=params
        )
        
        # Vérifier si la requête a réussi
        if response.status_code != 200:
            raise Exception(f"Erreur lors de la recherche sur Indeed: {response.status_code} - {response.text}")
        
        # Traiter les résultats
        data = response.json()
        results = []
        
        for job in data.get("results", []):
            # Extraire la ville et le pays de la localisation
            location_str = job.get("formattedLocation", "")
            city = location_str.split(",")[0].strip() if "," in location_str else location_str
            country = location_str.split(",")[-1].strip() if "," in location_str else "France"
            
            # Créer l'objet Location
            location_obj = Location(
                city=city,
                postal_code=None,
                region=None,
                country=country,
                formatted_address=location_str
            )
            
            # Créer l'objet JobPosting
            job_posting = JobPosting(
                job_id=job.get("jobkey", ""),
                title=job.get("jobtitle", ""),
                company=job.get("company", ""),
                location=location_obj,
                description=job.get("snippet", ""),
                url=job.get("url", ""),
                posted_date=job.get("date", datetime.now().strftime("%Y-%m-%d")),
                salary_range=None,
                job_type=None,
                required_skills=None,
                required_experience=None,
                required_education=None,
                source=JobSource.INDEED,
                raw_data=job
            )
            
            results.append(job_posting)
        
        return results


class GlassdoorClient(JobAPIClient):
    """Client pour l'API Glassdoor."""
    
    def __init__(self):
        """Initialise le client avec la clé API."""
        self.api_key = os.getenv("GLASSDOOR_API_KEY")
        self.base_url = "https://api.glassdoor.com/api/api.htm"
        if not self.api_key:
            raise ValueError("La clé API Glassdoor n'est pas configurée.")
    
    def search_jobs(self, job_title: str, location: Optional[str] = None, 
                   radius: int = 50, keywords: Optional[List[str]] = None, 
                   limit: int = 10) -> List[JobPosting]:
        """
        Recherche des offres d'emploi sur Glassdoor.
        
        Args:
            job_title: Le titre du poste recherché.
            location: Optionnel, la localisation (ville, région, pays).
            radius: Le rayon de recherche en km.
            keywords: Optionnel, des mots-clés supplémentaires.
            limit: Le nombre maximum de résultats à retourner.
            
        Returns:
            Une liste d'offres d'emploi.
        """
        # Construire les paramètres de recherche
        params = {
            "v": "1",
            "format": "json",
            "t.p": "API_KEY",  # Remplacer par le partner ID
            "t.k": self.api_key,
            "action": "jobs-prog",
            "countryId": "1",  # 1 pour les États-Unis, adapter selon le besoin
            "jobTitle": job_title,
            "numResults": limit
        }
        
        # Ajouter la localisation si spécifiée
        if location:
            params["city"] = location
            
        # Informer que les mots-clés supplémentaires sont disponibles mais non utilisés
        if keywords:
            print(f"INFO: {len(keywords)} compétences disponibles mais non ajoutées à la requête Glassdoor")
            # Note: Glassdoor ne permet pas d'ajouter des mots-clés supplémentaires
            # à la recherche, donc ces informations sont ignorées.
        
        # Effectuer la requête
        response = requests.get(
            self.base_url,
            params=params
        )
        
        # Vérifier si la requête a réussi
        if response.status_code != 200:
            raise Exception(f"Erreur lors de la recherche sur Glassdoor: {response.status_code} - {response.text}")
        
        # Traiter les résultats
        data = response.json()
        results = []
        
        for job in data.get("response", {}).get("jobListings", []):
            # Extraire la ville et le pays
            location_str = job.get("location", "")
            city = location_str.split(",")[0].strip() if "," in location_str else location_str
            country = "France"  # Par défaut, à adapter
            
            # Créer l'objet Location
            location_obj = Location(
                city=city,
                postal_code=None,
                region=None,
                country=country,
                formatted_address=location_str
            )
            
            # Créer l'objet JobPosting
            job_posting = JobPosting(
                job_id=str(job.get("jobListingId", "")),
                title=job.get("jobTitle", ""),
                company=job.get("employer", {}).get("name", ""),
                location=location_obj,
                description=job.get("jobDescription", ""),
                url=job.get("jobViewUrl", ""),
                posted_date=datetime.now().strftime("%Y-%m-%d"),  # Date exacte non disponible
                salary_range=None,
                job_type=None,
                required_skills=None,
                required_experience=None,
                required_education=None,
                source=JobSource.GLASSDOOR,
                raw_data=job
            )
            
            results.append(job_posting)
        
        return results 