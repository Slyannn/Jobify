"""
Routes API pour l'application AI Job Assistant.
"""
import base64
import json
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body, Depends
from pydantic import BaseModel
from starlette.responses import JSONResponse

from src.models.cv import CVData, CVAnalysisRequest, CVUpload
from src.models.job import JobSearchRequest, JobSearchResponse, JobPosting, JobRecommendationRequest
from src.agents.cv_analyzer import CVAnalyzerAgent
from src.agents.job_searcher import JobSearcherAgent
from src.agents.recommender import RecommenderAgent, RecommendationResult


# Création du router
router = APIRouter(
    prefix="/api",
    tags=["api"],
    responses={404: {"description": "Not found"}},
)


# Endpoint pour vérifier l'état de l'API
@router.get("/health")
async def health_check():
    """Vérifie l'état de l'API."""
    return {"status": "ok", "message": "API opérationnelle"}


# Endpoint pour analyser un CV
@router.post("/analyze-cv", response_model=CVData)
async def analyze_cv(request: CVAnalysisRequest):
    """
    Analyse un CV et extrait les informations pertinentes.
    """
    try:
        # Initialiser l'agent d'analyse de CV
        cv_analyzer = CVAnalyzerAgent()
        
        # Si des données CV sont déjà fournies, les renvoyer simplement
        if request.cv_data:
            return request.cv_data
        
        # Si un fichier CV est fourni, l'analyser
        if request.cv_upload:
            # Extraire les informations du CV
            cv_data = cv_analyzer.extract_from_pdf(request.cv_upload.file_content)
            return cv_data
        
        # Si aucune donnée ou fichier n'est fourni, lever une exception
        raise HTTPException(
            status_code=400,
            detail="Aucune donnée CV ou fichier CV fourni."
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'analyse du CV: {str(e)}"
        )


# Endpoint pour télécharger un CV
@router.post("/upload-cv", response_model=CVData)
async def upload_cv(file: UploadFile = File(...)):
    """
    Télécharge et analyse un CV.
    """
    try:
        # Vérifier le type de fichier
        if not file.filename.endswith((".pdf", ".PDF")):
            raise HTTPException(
                status_code=400,
                detail="Format de fichier non supporté. Seuls les fichiers PDF sont acceptés."
            )
        
        # Lire le contenu du fichier
        file_content = await file.read()
        
        # Encoder le contenu en base64
        file_content_base64 = base64.b64encode(file_content).decode("utf-8")
        
        # Initialiser l'agent d'analyse de CV
        cv_analyzer = CVAnalyzerAgent()
        
        # Extraire les informations du CV
        cv_data = cv_analyzer.extract_from_pdf(file_content_base64)
        
        return cv_data
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du téléchargement ou de l'analyse du CV: {str(e)}"
        )


# Endpoint pour rechercher des offres d'emploi
@router.post("/search-jobs", response_model=JobSearchResponse)
async def search_jobs(request: JobSearchRequest):
    """
    Recherche des offres d'emploi.
    """
    try:
        # Initialiser l'agent de recherche d'emploi
        job_searcher = JobSearcherAgent()
        
        # Rechercher des offres d'emploi
        response = job_searcher.search_jobs(request)
        
        return response
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la recherche d'emploi: {str(e)}"
        )


# Endpoint pour obtenir des recommandations
@router.post("/recommend", response_model=RecommendationResult)
async def recommend(request: JobRecommendationRequest):
    """
    Génère des recommandations d'emploi et d'amélioration de CV.
    """
    try:
        # Initialiser l'agent de recommandation
        recommender = RecommenderAgent()
        
        # Convertir cv_data en objet CVData
        if not request.cv_data:
            raise HTTPException(
                status_code=400,
                detail="Données CV manquantes."
            )
        
        # Construire des objets CVData et JobPosting à partir des dictionnaires
        try:
            # Créer l'objet CVData
            cv_data = CVData(**request.cv_data)
            
            # Créer les objets JobPosting
            job_postings = [JobPosting(**job) for job in request.job_postings]
            
            # Générer des recommandations
            recommendations = recommender.recommend(cv_data, job_postings)
            
            return recommendations
        
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Erreur de format des données: {str(e)}"
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération des recommandations: {str(e)}"
        )


# Endpoint pour le processus complet (analyse CV + recherche + recommandation)
@router.post("/complete-process", response_model=Dict[str, Any])
async def complete_process(
    cv_upload: Optional[CVUpload] = None,
    cv_data: Optional[Dict[str, Any]] = None,
    job_title: Optional[str] = None,
    location: Optional[str] = None,
    sources: Optional[List[str]] = None
):
    """
    Exécute le processus complet: analyse un CV, recherche des offres d'emploi et génère des recommandations.
    """
    try:
        # 1. Analyser le CV
        cv_analyzer = CVAnalyzerAgent()
        
        if cv_upload:
            analyzed_cv = cv_analyzer.extract_from_pdf(cv_upload.file_content)
        elif cv_data:
            analyzed_cv = CVData(**cv_data)
        else:
            raise HTTPException(
                status_code=400,
                detail="Aucune donnée CV ou fichier CV fourni."
            )
        
        # 2. Déterminer le titre du poste recherché
        job_title_to_search = job_title or analyzed_cv.desired_job
        
        if not job_title_to_search:
            raise HTTPException(
                status_code=400,
                detail="Impossible de déterminer le poste recherché."
            )
        
        # 3. Rechercher des offres d'emploi
        job_searcher = JobSearcherAgent()
        
        # Créer la requête de recherche
        search_request = JobSearchRequest(
            job_title=job_title_to_search,
            location=location,
            cv_data=analyzed_cv.dict(),
            sources=sources
        )
        
        # Rechercher des offres d'emploi
        search_response = job_searcher.search_jobs(search_request)
        
        # 4. Générer des recommandations
        recommender = RecommenderAgent()
        
        # Vérifier s'il y a des offres d'emploi
        if not search_response.results:
            return {
                "cv_data": analyzed_cv,
                "job_search": search_response,
                "recommendations": {
                    "ranked_jobs": [],
                    "cv_improvement_suggestions": {
                        "content": ["Pas assez d'offres d'emploi pour générer des recommandations"],
                        "structure": [],
                        "presentation": []
                    },
                    "highlighted_skills": [],
                    "missing_skills": [],
                    "career_advice": "Aucune offre d'emploi trouvée. Essayez d'élargir votre recherche ou de modifier les mots-clés."
                }
            }
        
        # Générer des recommandations
        recommendations = recommender.recommend(analyzed_cv, search_response.results)
        
        # 5. Renvoyer tous les résultats
        return {
            "cv_data": analyzed_cv,
            "job_search": search_response,
            "recommendations": recommendations
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du processus complet: {str(e)}"
        ) 