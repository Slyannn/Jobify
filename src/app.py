"""
Application Streamlit pour l'interface utilisateur du chatbot.
"""
import streamlit as st
import os
import sys
from typing import Optional
import base64

# Ajout du répertoire parent au chemin Python pour résoudre les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports relatifs depuis le projet
from agents.chatbot import ChatbotAgent
from models.cv import CVData
from utils.pdf_parser import PDFParser

# Configuration de la page
st.set_page_config(
    page_title="Assistant IA de Recherche d'Emploi",
    page_icon="💼",
    layout="wide"
)

# Initialisation de l'agent chatbot
@st.cache_resource
def get_chatbot():
    return ChatbotAgent()

# Initialisation du parser PDF
@st.cache_resource
def get_pdf_parser():
    return PDFParser()

# Fonction pour convertir un fichier PDF en base64
def get_base64_from_file(uploaded_file) -> str:
    return base64.b64encode(uploaded_file.getvalue()).decode()

def main():
    st.title("💼 Assistant IA de Recherche d'Emploi")
    
    # Initialisation de la session
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Ajouter le message d'accueil au démarrage
        welcome_message = """Bonjour ! 👋 Je suis votre assistant IA de recherche d'emploi.

Je peux vous aider à :
- 📄 Analyser votre CV et proposer des améliorations
- 🔍 Rechercher des offres d'emploi adaptées à votre profil
- 💡 Obtenir des recommandations personnalisées pour votre carrière
- 🎯 Préparer vos entretiens d'embauche

Pour commencer, téléchargez votre CV dans la barre latérale, puis posez-moi vos questions !"""
        
        st.session_state.messages.append({"role": "assistant", "content": welcome_message})
        
    if "cv_data" not in st.session_state:
        st.session_state.cv_data = None
    
    # Sidebar pour le téléchargement du CV
    with st.sidebar:
        st.header("📄 Votre CV")
        uploaded_file = st.file_uploader("Téléchargez votre CV (PDF)", type=["pdf"])
        
        if uploaded_file is not None:
            try:
                # Convertir le fichier en base64
                pdf_base64 = get_base64_from_file(uploaded_file)
                
                # Extraire le texte du PDF
                pdf_parser = get_pdf_parser()
                pdf_text = pdf_parser.extract_text_from_base64(pdf_base64)
                
                # Analyser le CV
                chatbot = get_chatbot()
                st.session_state.cv_data = chatbot.cv_analyzer.extract_from_text(pdf_text)
                
                st.success("CV analysé avec succès !")
            except Exception as e:
                st.error(f"Erreur lors de l'analyse du CV : {str(e)}")
    
    # Zone de chat
    st.header("💬 Chat")
    
    # Afficher l'historique des messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Zone de saisie
    if prompt := st.chat_input("Posez votre question..."):
        # Ajouter le message de l'utilisateur à l'historique
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Générer la réponse
        with st.chat_message("assistant"):
            chatbot = get_chatbot()
            response = chatbot.process_message(prompt, st.session_state.cv_data)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main() 