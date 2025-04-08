"""
Point d'entrée principal de l'application AI Job Assistant.
Initialise l'application FastAPI et importe les routes.
"""
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Charger les variables d'environnement
load_dotenv()

# Créer l'application FastAPI
app = FastAPI(
    title="AI Job Assistant",
    description="Système d'assistance IA pour la recherche d'emploi",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # A adapter en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importer les routes API
from src.api.routes import router
app.include_router(router)

# Point d'entrée pour l'exécution directe
if __name__ == "__main__":
    host = os.getenv("APP_HOST", "localhost")
    port = int(os.getenv("APP_PORT", 8000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=debug
    ) 