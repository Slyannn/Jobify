"""
Agent conversationnel basé sur LangChain qui sert d'interface utilisateur pour interagir avec les autres agents.
"""
import os
import sys
from typing import Dict, Any, Optional, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

# Ajout du répertoire parent au chemin Python pour résoudre les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.cv_analyzer import CVAnalyzerAgent
from agents.job_searcher import JobSearcherAgent
from agents.recommender import RecommenderAgent
from models.cv import CVData
from models.job import JobPosting, JobSearchRequest

class ChatbotAgent:
    """Agent conversationnel qui orchestre les interactions avec les autres agents."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise l'agent conversationnel.
        
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
            temperature=0.7
        )
        
        # Initialisation des autres agents
        self.cv_analyzer = CVAnalyzerAgent(api_key)
        self.job_searcher = JobSearcherAgent(api_key)
        self.recommender = RecommenderAgent(api_key)
        
        # Historique de la conversation
        self.conversation_history: List[Dict[str, str]] = []
        
        # Construction du prompt de conversation
        self.chat_prompt = ChatPromptTemplate.from_template("""
        Tu es un assistant conversationnel spécialisé dans l'aide à la recherche d'emploi.
        Tu peux aider les utilisateurs à:
        1. Analyser leur CV
        2. Rechercher des offres d'emploi
        3. Obtenir des recommandations personnalisées
        4. Améliorer leur CV
        5. Préparer des entretiens
        
        Historique de la conversation:
        {history}
        
        Message de l'utilisateur: {user_message}
        
        Réponds de manière naturelle et conversationnelle, en identifiant l'intention de l'utilisateur
        et en utilisant les agents appropriés pour répondre à sa demande.
        """)
        
        # Construction de la chaîne de conversation
        self.conversation_chain = (
            self.chat_prompt 
            | self.llm 
            | StrOutputParser()
        )
    
    def _update_history(self, user_message: str, bot_response: str):
        """Met à jour l'historique de la conversation."""
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": bot_response})
    
    def _format_history(self) -> str:
        """Formate l'historique de la conversation pour le prompt."""
        formatted_history = ""
        for message in self.conversation_history[-6:]:  # Garde les 3 derniers échanges
            role = "Utilisateur" if message["role"] == "user" else "Assistant"
            formatted_history += f"{role}: {message['content']}\n\n"
        return formatted_history
    
    def _format_cv_analysis(self, cv_data: CVData) -> str:
        """Formate l'analyse du CV de manière lisible."""
        response = "Voici l'analyse de votre CV :\n\n"
        
        # Informations personnelles
        if cv_data.full_name:
            response += f"**Nom complet** : {cv_data.full_name}\n"
        if cv_data.email:
            response += f"**Email** : {cv_data.email}\n"
        if cv_data.phone:
            response += f"**Téléphone** : {cv_data.phone}\n"
        if cv_data.location:
            response += f"**Localisation** : {cv_data.location}\n"
        
        # Poste recherché
        if cv_data.desired_job:
            response += f"\n**Poste recherché** : {cv_data.desired_job}\n"
        
        # Compétences
        if cv_data.skills:
            response += "\n**Compétences clés** :\n"
            for skill in cv_data.skills:
                response += f"- {skill}\n"
        
        # Expérience professionnelle
        if cv_data.experiences:
            response += "\n**Expérience professionnelle** :\n"
            for exp in cv_data.experiences:
                response += f"\n**{exp.position}** chez {exp.company}\n"
                if exp.start_date and exp.end_date:
                    response += f"Période : {exp.start_date} - {exp.end_date}\n"
                if exp.location:
                    response += f"Lieu : {exp.location}\n"
                if exp.description:
                    response += f"Description : {exp.description}\n"
        # Projets personnels et académiques
        if cv_data.projects:
            response += "\n**Projets personnels et académiques** :\n"
            for proj in cv_data.projects:
                response += f"\n**{proj.title}**\n"
                if proj.start_date and proj.end_date:
                    response += f"Période : {proj.start_date} - {proj.end_date}\n"
                if proj.description:
                    response += f"Description : {proj.description}\n"
                if proj.technologies:
                    response += f"Technologies : {proj.technologies}\n"
                if proj.url:
                    response += f"URL : {proj.url}\n"
        
        # Formation
        if cv_data.education:
            response += "\n**Formation** :\n"
            for edu in cv_data.education:
                response += f"\n**{edu.diploma} en {edu.field_of_study}**\n"
                response += f"Établissement : {edu.institution}\n"
                if edu.start_date and edu.end_date:
                    response += f"Période : {edu.start_date} - {edu.end_date}\n"
                if edu.description:
                    response += f"Description : {edu.description}\n"
        
        # Langues
        if cv_data.languages:
            response += "\n**Langues** :\n"
            for lang in cv_data.languages:
                response += f"- {lang}\n"
        
        # Résumé
        if cv_data.summary:
            response += f"\n**Résumé** :\n{cv_data.summary}\n"
        
        return response
    
    def _format_recommendation_result(self, result) -> str:
        """Formate le résultat des recommandations de manière lisible."""
        response = "Voici mes recommandations pour vous :\n\n"
        
        # Compétences mises en avant
        if result.highlighted_skills:
            response += "**Compétences à mettre en avant** :\n"
            for skill in result.highlighted_skills:
                response += f"- {skill}\n"
            response += "\n"
        
        # Compétences manquantes
        if result.missing_skills:
            response += "**Compétences à développer** :\n"
            for skill in result.missing_skills:
                response += f"- {skill}\n"
            response += "\n"
        
        # Améliorations du CV
        if result.cv_improvements:
            response += "**Améliorations suggérées pour votre CV** :\n"
            for improvement in result.cv_improvements:
                response += f"- {improvement}\n"
            response += "\n"
        
        # Conseils de carrière
        if result.career_advice:
            response += f"**Conseils de carrière** :\n{result.career_advice}\n\n"
        
        # Offres d'emploi classées
        if result.ranked_jobs:
            response += "**Offres d'emploi recommandées** :\n"
            for job in result.ranked_jobs:
                response += f"- **{job.get('title', 'Poste')}** chez {job.get('company', 'Entreprise')}\n"
                if 'match_score' in job:
                    response += f"  Score de correspondance : {job['match_score']}\n"
                if 'reason' in job:
                    response += f"  Raison : {job['reason']}\n"
                response += "\n"
        
        return response
    
    def _extract_location_from_message(self, message: str) -> Optional[str]:
        """
        Extrait la localisation mentionnée dans le message de l'utilisateur.
        Recherche les noms de grandes villes françaises ou les codes postaux/départements.
        
        Args:
            message: Message de l'utilisateur.
            
        Returns:
            La localisation extraite ou None si non trouvée.
        """
        # Liste des villes connues à rechercher
        known_cities = ["paris", "lyon", "marseille", "toulouse", "nice", "bordeaux", "lille"]
        
        # Convertir le message en minuscules pour la comparaison
        message_lower = message.lower()
        
        # Rechercher des mentions de villes connues
        for city in known_cities:
            # Vérifier si la ville est mentionnée avec des limites de mots
            if f" {city} " in f" {message_lower} " or f" {city}," in f" {message_lower} " or f" {city}." in f" {message_lower} ":
                return city
            
            # Vérifier les expressions communes
            location_phrases = [
                f"à {city}", f"dans {city}", f"sur {city}", 
                f"vers {city}", f"autour de {city}", f"près de {city}",
                f"en région {city}", f"ville de {city}"
            ]
            for phrase in location_phrases:
                if phrase in message_lower:
                    return city
        
        # Rechercher des codes postaux (format 5 chiffres) ou codes département (format 2 chiffres)
        import re
        postal_code_match = re.search(r'(?<!\d)(\d{5})(?!\d)', message)
        if postal_code_match:
            return postal_code_match.group(1)
            
        dept_code_match = re.search(r'département (\d{2})', message_lower)
        if dept_code_match:
            return dept_code_match.group(1)
        
        return None

    def process_message(self, user_message: str, cv_data: Optional[CVData] = None) -> str:
        """
        Traite un message de l'utilisateur et génère une réponse appropriée.
        
        Args:
            user_message: Message de l'utilisateur.
            cv_data: Données du CV de l'utilisateur si disponibles.
            
        Returns:
            Réponse de l'assistant.
        """
        # Analyse l'intention de l'utilisateur
        intent = self._analyze_intent(user_message)
        
        # Traite le message selon l'intention détectée
        if intent == "analyze_cv":
            if not cv_data:
                return "Je ne peux pas analyser votre CV car je n'ai pas reçu de données CV. Veuillez d'abord télécharger votre CV."
            response = self._format_cv_analysis(cv_data)
        
        elif intent == "improve_cv":
            if not cv_data:
                return "Pour suggérer des améliorations pour votre CV, veuillez d'abord télécharger votre CV."
            try:
                recommendations = self.recommender.recommend(cv_data, [])
                response = "Voici mes suggestions pour améliorer votre CV :\n\n"
                if recommendations.cv_improvements:
                    for improvement in recommendations.cv_improvements:
                        response += f"- {improvement}\n"
                else:
                    response += "Je n'ai pas de suggestions spécifiques pour améliorer votre CV. Il semble bien structuré pour le poste que vous recherchez."
            except Exception as e:
                response = f"Désolé, une erreur s'est produite lors de la génération des suggestions d'amélioration. Veuillez réessayer plus tard.\nErreur : {str(e)}"
        
        elif intent == "search_jobs":
            if not cv_data:
                return "Pour une recherche d'emploi pertinente, je vous conseille de d'abord télécharger votre CV."
            try:
                # Extraire la localisation spécifiée dans le message
                specified_location = self._extract_location_from_message(user_message)
                
                # Utiliser la localisation spécifiée ou celle du CV par défaut
                location = specified_location or cv_data.location or ""
                
                # Si une ville a été spécifiée, informer l'utilisateur
                location_info = ""
                if specified_location and specified_location != cv_data.location:
                    location_info = f"\n\nRecherche effectuée pour la localisation: **{specified_location.capitalize()}**"
                
                search_request = JobSearchRequest(
                    job_title=cv_data.desired_job or "",
                    location=location,
                    radius=70,
                    keywords=cv_data.skills or [],
                    limit_per_source=5
                )
                try:
                    search_results = self.job_searcher.search_jobs(search_request)
                    if search_results.total_count > 0:
                        if search_results.total_count == 1:
                            response = f"J'ai trouvé {search_results.total_count} offre d'emploi correspondant à votre profil."
                        else:
                            response = f"J'ai trouvé {search_results.total_count} offres d'emploi correspondant à votre profil."
                        
                        # Ajouter l'info de localisation si spécifiée
                        response += location_info
                        
                        response += "\n\n### Offres trouvées:\n"
                        for i, job in enumerate(search_results.results[:5]):  # Limite à 5 résultats affichés
                            response += f"\n#### {i+1}. {job.title} chez {job.company}\n\n"
                            
                            # Affichage de la localisation
                            if hasattr(job.location, 'city') and job.location.city:
                                if hasattr(job.location, 'postal_code') and job.location.postal_code:
                                    response += f"📍 **Localisation**: {job.location.city}, {job.location.postal_code}, {job.location.country}\n\n"
                                else:
                                    response += f"📍 **Localisation**: {job.location.city}, {job.location.country}\n\n"
                            elif isinstance(job.location, str):
                                response += f"📍 **Localisation**: {job.location}\n\n"
                            
                            # Affichage du type de contrat
                            if hasattr(job, 'job_type') and job.job_type:
                                response += f"📋 **Type de contrat**: {job.job_type}\n\n"
                            
                            # Affichage du salaire
                            if hasattr(job, 'salary_range') and job.salary_range:
                                response += f"💰 **Salaire**: {job.salary_range}\n\n"
                            
                            # Affichage de la description
                            if job.description:
                                # Limiter la description à 200 caractères
                                max_desc_length = 200
                                if len(job.description) > max_desc_length:
                                    # Trouver le dernier espace avant la limite pour ne pas couper un mot
                                    cutoff = job.description[:max_desc_length].rfind(' ')
                                    if cutoff == -1:  # Si pas d'espace trouvé, couper à la limite
                                        cutoff = max_desc_length
                                    response += f"📝 **Description**: {job.description[:cutoff]}...\n\n"
                                else:
                                    response += f"📝 **Description**: {job.description}\n\n"
                            
                            # Affichage du lien vers l'offre
                            if job.url:
                                response += f"🔗 [Voir l'offre complète]({job.url})\n\n"
                            
                            # Ajouter un séparateur entre les offres
                            if i < min(len(search_results.results), 5) - 1:
                                response += "---\n"
                    else:
                        response = "Je n'ai pas trouvé d'offres d'emploi correspondant à votre profil. Essayez d'élargir vos critères de recherche."
                except ValueError as ve:
                    if "Aucune source d'emploi n'est disponible" in str(ve):
                        response = "Actuellement, je ne peux pas effectuer de recherche d'emploi car aucune source n'est correctement configurée. Pour utiliser cette fonctionnalité, l'administrateur doit configurer les clés API pour les plateformes de recherche d'emploi."
                    else:
                        raise
            except Exception as e:
                error_message = str(e)
                if "401" in error_message:
                    response = "Je ne peux pas accéder aux offres d'emploi pour le moment car les clés API des plateformes de recherche d'emploi ne sont pas correctement configurées. Veuillez contacter l'administrateur pour configurer les sources d'emploi."
                else:
                    response = f"Désolé, une erreur s'est produite lors de la recherche d'emploi. Veuillez réessayer plus tard.\nErreur : {error_message}"
        
        elif intent == "get_recommendations":
            if not cv_data:
                return "Pour obtenir des recommandations personnalisées, je vous conseille de d'abord télécharger votre CV."
            try:
                recommendations = self.recommender.recommend(cv_data, [])
                response = self._format_recommendation_result(recommendations)
            except Exception as e:
                response = f"Désolé, une erreur s'est produite lors de la génération des recommandations. Veuillez réessayer plus tard.\nErreur : {str(e)}"
        
        else:
            # Réponse conversationnelle générale
            response = self.conversation_chain.invoke({
                "history": self._format_history(),
                "user_message": user_message
            })
        
        # Met à jour l'historique
        self._update_history(user_message, response)
        
        return response
    
    def _analyze_intent(self, message: str) -> str:
        """
        Analyse l'intention de l'utilisateur à partir de son message.
        
        Args:
            message: Message de l'utilisateur.
            
        Returns:
            Intention détectée.
        """
        intent_prompt = ChatPromptTemplate.from_template("""
        Analyse ce message et détermine l'intention de l'utilisateur parmi:
        - analyze_cv: Demande d'analyse de CV
        - improve_cv: Demande d'amélioration du CV
        - search_jobs: Demande de recherche d'emploi (incluant les demandes d'offres d'emploi dans une ville spécifique)
        - get_recommendations: Demande de recommandations
        - other: Autre demande
        
        Quelques exemples:
        - "Cherche un emploi à Paris" -> search_jobs
        - "Montre-moi des offres près de Lyon" -> search_jobs
        - "Offres d'emploi à Marseille" -> search_jobs
        - "Quelles sont les opportunités près de chez moi?" -> search_jobs
        
        Message: {message}
        
        Réponds UNIQUEMENT avec l'une des intentions ci-dessus.
        """)
        
        intent_chain = intent_prompt | self.llm | StrOutputParser()
        return intent_chain.invoke({"message": message}) 