# Salesforce CRM — Data Quality Pipeline

Projet de démonstration : audit de la qualité des données extraites de Salesforce CRM, avant entraînement d'un modèle IA.

## Contexte

Une équipe IA veut construire un modèle de scoring commercial sur les données Salesforce. Ce pipeline audite la qualité des 4 objets CRM principaux avant tout entraînement.

## Objets couverts

| Objet | Enregistrements | Score DQ |
|---|---|---|
| Account | 301 | 98.7 / 100 |
| Contact | 601 | 98.9 / 100 |
| Lead | 400 | 96.3 / 100 |
| Opportunity | 500 | 60.6 / 100 ⚠️ |

## Dimensions Data Quality analysées

- **Complétude** — champs obligatoires manquants
- **Unicité** — doublons exacts et approximatifs (fuzzy matching)
- **Validité** — formats, picklists Salesforce, plages de valeurs
- **Cohérence** — FK orphelines, dates incohérentes
- **Règle Métier** — logique CRM (IsConverted/ConvertedDate, StageName/IsWon…)

## Structure du projet

```
01_generate_salesforce_data.py   → Simule un export Salesforce (Account, Contact, Lead, Opportunity)
02_sql_dq_checks.py              → 51 checks SQL par dimension DQ
03_python_dq_pipeline.py         → Pipeline Python + rapport HTML interactif
GUIDE_DEMO.md                    → Script de présentation client
```

## Installation & lancement

```bash
pip install pandas numpy faker
python 01_generate_salesforce_data.py
python 02_sql_dq_checks.py
python 03_python_dq_pipeline.py
# Ouvrir salesforce_dq_report.html dans le navigateur
```

## Stack technique

- **Python** : pandas, numpy, faker, sqlite3
- **SQL** : SQLite (portable) — requêtes transposables sur Snowflake / BigQuery / Redshift
- **Rapport** : HTML + Chart.js (bar chart + radar chart)
- **Connexion Salesforce réelle** : remplacer l'étape 01 par `simple_salesforce` + requêtes SOQL

## Anomalies intentionnellement injectées (démo)

- FK orphelines (AccountId fantôme)
- Emails dupliqués entre Contact et Lead
- IsConverted incohérent avec ConvertedDate
- 380 opportunités pipeline avec CloseDate dépassée
- Valeurs hors picklist Salesforce native
- Dates de création dans le futur
