"""
Modèles de données pour les offres d'emploi et les recherches.
"""
from typing import List, Optional, Dict, Any
from enum import Enum


class JobSource(str, Enum):
    """Sources d'offres d'emploi supportées."""
    FRANCE_TRAVAIL = "france_travail"
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"


class Location:
    """Localisation d'une offre d'emploi."""
    
    def __init__(
        self,
        city: str,
        postal_code: Optional[str] = None,
        region: Optional[str] = None,
        country: str = "France",
        formatted_address: Optional[str] = None
    ):
        self.city = city
        self.postal_code = postal_code
        self.region = region
        self.country = country
        self.formatted_address = formatted_address or f"{city}, {country}"
    
    def __str__(self) -> str:
        """Représentation en chaîne de caractères de la localisation."""
        parts = []
        if self.city:
            parts.append(self.city)
        if self.postal_code:
            parts.append(self.postal_code)
        if self.region and self.region not in (self.city, self.postal_code):
            parts.append(self.region)
        if self.country:
            parts.append(self.country)
        
        return ", ".join(parts)


class JobPosting:
    """Offre d'emploi."""
    
    def __init__(
        self,
        job_id: str,
        title: str,
        company: str,
        location: Location,
        description: str,
        url: str,
        posted_date: str,
        salary_range: Optional[str] = None,
        job_type: Optional[str] = None,
        required_skills: Optional[List[str]] = None,
        required_experience: Optional[str] = None,
        required_education: Optional[str] = None,
        source: JobSource = None,
        raw_data: Optional[Dict[str, Any]] = None
    ):
        self.job_id = job_id
        self.title = title
        self.company = company
        self.location = location
        self.description = description
        self.url = url
        self.posted_date = posted_date
        self.salary_range = salary_range
        self.job_type = job_type
        self.required_skills = required_skills or []
        self.required_experience = required_experience
        self.required_education = required_education
        self.source = source
        self.raw_data = raw_data
    
    def __str__(self) -> str:
        """Représentation en chaîne de caractères de l'offre d'emploi."""
        return f"{self.title} chez {self.company} - {self.location}"


class JobSearchRequest:
    """Requête de recherche d'emploi."""
    
    def __init__(
        self,
        job_title: str,
        location: Optional[str] = None,
        radius: int = 50,
        keywords: Optional[List[str]] = None,
        limit_per_source: int = 10,
        cv_data: Optional[Any] = None
    ):
        self.job_title = job_title
        self.location = location
        self.radius = radius
        self.keywords = keywords or []
        self.limit_per_source = limit_per_source
        self.cv_data = cv_data


class JobSearchResponse:
    """Résultat d'une recherche d'emploi."""
    
    def __init__(
        self,
        query: JobSearchRequest,
        results: List[JobPosting],
        available_sources: List[str],
        failed_sources: List[str],
        total_count: int
    ):
        self.query = query
        self.results = results
        self.available_sources = available_sources
        self.failed_sources = failed_sources
        self.total_count = total_count


class JobRecommendationRequest:
    """Requête de recommandation d'emploi."""
    
    def __init__(
        self,
        cv_data: Dict[str, Any],
        job_postings: List[JobPosting]
    ):
        self.cv_data = cv_data
        self.job_postings = job_postings 