"""
Agent de recommandation qui analyse les résultats des agents d'analyse de CV et de recherche d'emploi
pour recommander les meilleures offres et suggérer des améliorations pour le CV.
"""
import os
import json
from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from models.cv import CVData
from models.job import JobPosting

class RecommendationResult:
    """Résultat des recommandations."""
    def __init__(
        self,
        ranked_jobs: List[JobPosting],
        cv_improvements: List[str],
        highlighted_skills: List[str],
        missing_skills: List[str],
        career_advice: str
    ):
        self.ranked_jobs = ranked_jobs
        self.cv_improvements = cv_improvements
        self.highlighted_skills = highlighted_skills
        self.missing_skills = missing_skills
        self.career_advice = career_advice
    
    def __str__(self) -> str:
        """Formate l'objet en chaîne lisible."""
        result = "Recommandations:\n\n"
        
        if self.highlighted_skills:
            result += "Compétences à mettre en avant:\n"
            for skill in self.highlighted_skills:
                result += f"- {skill}\n"
            result += "\n"
        
        if self.missing_skills:
            result += "Compétences à développer:\n"
            for skill in self.missing_skills:
                result += f"- {skill}\n"
            result += "\n"
        
        if self.cv_improvements:
            result += "Améliorations du CV:\n"
            for improvement in self.cv_improvements:
                result += f"- {improvement}\n"
            result += "\n"
        
        if self.career_advice:
            result += f"Conseils de carrière:\n{self.career_advice}\n\n"
        
        return result

class RecommenderAgent:
    """Agent qui analyse les résultats des agents précédents pour fournir des recommandations."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise l'agent de recommandation.
        
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
            temperature=0.3
        )
        
        # Construction du prompt de recommandation
        self.recommendation_prompt = ChatPromptTemplate.from_template("""
        Tu es un conseiller en carrière expérimenté. Analyse ce CV et ces offres d'emploi pour fournir des recommandations.
        
        CV du candidat:
        {cv_data}
        
        Offres d'emploi:
        {job_postings}
        
        Ta tâche est de:
        1. Évaluer la correspondance entre le CV et les offres d'emploi
        2. Classer les offres d'emploi par pertinence
        3. Identifier les compétences clés du candidat
        4. Identifier les compétences manquantes
        5. Proposer des améliorations pour le CV
        6. Donner des conseils de carrière
        
        Réponds au format JSON suivant:
        {{
            "ranked_jobs": [
                {{
                    "title": "Titre du poste",
                    "company": "Nom de l'entreprise",
                    "match_score": 0.95,
                    "reason": "Raison de la correspondance"
                }}
            ],
            "cv_improvements": [
                "Suggestion d'amélioration 1",
                "Suggestion d'amélioration 2"
            ],
            "highlighted_skills": [
                "Compétence clé 1",
                "Compétence clé 2"
            ],
            "missing_skills": [
                "Compétence manquante 1",
                "Compétence manquante 2"
            ],
            "career_advice": "Conseil de carrière personnalisé"
        }}
        
        Même s'il n'y a pas d'offres d'emploi à évaluer, fournir quand même des suggestions pour améliorer le CV, identifier les compétences clés et manquantes, et donner des conseils de carrière basés uniquement sur le CV.
        """)
        
        # Construction de la chaîne de recommandation
        self.recommendation_chain = (
            self.recommendation_prompt 
            | self.llm 
            | StrOutputParser()
        )
    
    def _parse_json_response(self, response: str) -> dict:
        """
        Parse la réponse JSON de l'agent.
        
        Args:
            response: Réponse textuelle de l'agent.
            
        Returns:
            Données parsées.
        """
        try:
            # Recherche du JSON dans la réponse
            start = response.find('{')
            end = response.rfind('}') + 1
            if start == -1 or end == 0:
                raise ValueError("Pas de JSON trouvé dans la réponse")
            
            json_str = response[start:end]
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Erreur de parsing JSON: {str(e)}")
    
    def _format_cv_data(self, cv_data: CVData) -> str:
        """Formate les données du CV pour le prompt."""
        formatted = f"""
        Poste recherché: {cv_data.desired_job}
        Localisation: {cv_data.location}
        
        Compétences:
        {', '.join(cv_data.skills)}
        
        Expérience professionnelle:
        """
        for exp in cv_data.experiences:
            formatted += f"""
            - {exp.position} chez {exp.company}
              Période: {exp.start_date} - {exp.end_date}
              Description: {exp.description}
            """
        
        formatted += "\nFormation:"
        for edu in cv_data.education:
            formatted += f"""
            - {edu.diploma} en {edu.field_of_study}
              Établissement: {edu.institution}
              Description: {edu.description}
            """
        
        return formatted
    
    def _format_job_postings(self, job_postings: List[JobPosting]) -> str:
        """Formate les offres d'emploi pour le prompt."""
        if not job_postings:
            return "Aucune offre d'emploi n'est disponible pour le moment."
            
        formatted = ""
        for job in job_postings:
            formatted += f"""
            - {job.title} chez {job.company}
              Localisation: {job.location}
              Description: {job.description}
              Compétences requises: {', '.join(job.required_skills)}
            """
        return formatted
    
    def recommend(self, cv_data: CVData, job_postings: List[JobPosting]) -> RecommendationResult:
        """
        Génère des recommandations basées sur le CV et les offres d'emploi.
        
        Args:
            cv_data: Données du CV.
            job_postings: Liste des offres d'emploi.
            
        Returns:
            Résultat des recommandations.
        """
        # Formatage des données pour le prompt
        formatted_cv = self._format_cv_data(cv_data)
        formatted_jobs = self._format_job_postings(job_postings)
        
        # Génération des recommandations
        response = self.recommendation_chain.invoke({
            "cv_data": formatted_cv,
            "job_postings": formatted_jobs
        })
        
        # Parsing de la réponse
        try:
            parsed_response = self._parse_json_response(response)
            
            # Création du résultat
            return RecommendationResult(
                ranked_jobs=parsed_response.get("ranked_jobs", []),
                cv_improvements=parsed_response.get("cv_improvements", []),
                highlighted_skills=parsed_response.get("highlighted_skills", []),
                missing_skills=parsed_response.get("missing_skills", []),
                career_advice=parsed_response.get("career_advice", "")
            )
        except Exception as e:
            raise ValueError(f"Erreur lors de la génération des recommandations: {str(e)}") 