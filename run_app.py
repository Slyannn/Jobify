"""
Script de lancement pour l'application Streamlit.
"""
import os
import subprocess
import sys
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

def main():
    # Vérification de la présence de la clé API OpenAI
    if not os.getenv("OPENAI_API_KEY"):
        print("ERREUR: La variable d'environnement OPENAI_API_KEY n'est pas définie.")
        print("Veuillez créer un fichier .env à la racine du projet avec votre clé API OpenAI:")
        print("OPENAI_API_KEY=votre_clé_api")
        sys.exit(1)
    
    # Chemin vers l'application Streamlit
    app_path = os.path.join("src", "app.py")
    
    # Vérification que le fichier existe
    if not os.path.exists(app_path):
        print(f"ERREUR: Le fichier {app_path} n'existe pas.")
        sys.exit(1)
    
    print("Démarrage de l'application...")
    
    # Lancement de l'application Streamlit
    subprocess.run(["streamlit", "run", app_path], check=True)

if __name__ == "__main__":
    main() 