# Assistant IA de Recherche d'Emploi

Une application Streamlit qui utilise l'IA pour aider les chercheurs d'emploi à analyser leur CV, trouver des offres d'emploi pertinentes et préparer leurs entretiens.

## Fonctionnalités

- **Analyse de CV**: Extraction automatique des compétences, expériences, et formation
- **Recherche d'emploi**: Intégration avec l'API France Travail pour trouver des offres pertinentes
- **Recommandations personnalisées**: Suggestions d'améliorations du CV basées sur les offres disponibles
- **Préparation aux entretiens**: Conseils et simulations d'entretiens d'embauche
- **Interface conversationnelle**: Interaction naturelle via un chatbot

## Installation

### Prérequis

- Python 3.8+
- Pip (gestionnaire de paquets Python)

### Étapes d'installation

1. Clonez ce dépôt:
   ```
   git clone https://github.com/votre-utilisateur/ai_job_assistant.git
   cd ai_job_assistant
   ```

2. Créez un environnement virtuel:
   ```
   python -m venv venv
   source venv/bin/activate  # Sur Windows: venv\Scripts\activate
   ```

3. Installez les dépendances:
   ```
   pip install -r requirements.txt
   ```

4. Configurez les API (optionnel):
   - Créez un fichier `.env` à la racine du projet avec vos clés API:
     ```
     OPENAI_API_KEY=your_openai_api_key
     FRANCE_TRAVAIL_CLIENT_ID=your_france_travail_client_id
     FRANCE_TRAVAIL_CLIENT_SECRET=your_france_travail_client_secret
     ```

## Utilisation

1. Lancez l'application:
   ```
   python run_app.py
   ```

2. Ouvrez votre navigateur à l'adresse: `http://localhost:8501`

3. Téléchargez votre CV au format PDF dans la barre latérale

4. Interagissez avec le chatbot pour:
   - Analyser votre CV
   - Rechercher des offres d'emploi
   - Obtenir des recommandations personnalisées
   - Préparer vos entretiens

## Structure du projet

```
ai_job_assistant/
├── src/                    # Code source principal
│   ├── agents/             # Agents d'IA (analyseur de CV, recherche d'emploi, etc.)
│   ├── models/             # Modèles de données (CV, offres d'emploi, etc.)
│   ├── utils/              # Utilitaires (parseur PDF, clients API, etc.)
│   └── app.py              # Application Streamlit principale
├── requirements.txt        # Dépendances du projet
└── run_app.py              # Script de lancement
```

## Technologies utilisées

- **Streamlit**: Interface utilisateur
- **LangChain**: Framework d'IA conversationnelle
- **OpenAI**: Modèles GPT-4o pour l'analyse et la génération de contenu
- **France Travail API**: Recherche d'offres d'emploi
- **PyPDF2**: Extraction de texte à partir de PDF

## Licence

Ce projet est sous licence MIT - voir le fichier LICENSE pour plus de détails. 