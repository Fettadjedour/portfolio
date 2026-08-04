# Guide de démo — Salesforce CRM Data Quality Pipeline

## Contexte du projet

**Client fictif :** Une entreprise B2B qui utilise Salesforce comme CRM central.
Son équipe IA veut construire un **modèle de scoring commercial** (prédiction de closing d'opportunités)
mais les données Salesforce ne sont pas fiables. Tu es mandatée pour auditer la qualité
et proposer un plan de remédiation.

---

## Comment lancer le projet (3 commandes)

```bash
# 1. Installer les dépendances
pip install pandas numpy faker

# 2. Générer les données Salesforce simulées
python 01_generate_salesforce_data.py

# 3. Lancer les checks SQL
python 02_sql_dq_checks.py

# 4. Générer le rapport HTML interactif
python 03_python_dq_pipeline.py

# → Ouvrir salesforce_dq_report.html dans le navigateur
```

---

## Script de présentation client (10 min)

### 1. Accroche (1 min)
> *"Avant de construire votre modèle de scoring commercial,
> j'ai audité vos données Salesforce. Ce que j'ai trouvé va
> directement impacter la qualité de vos prédictions IA."*

### 2. Montrer le rapport HTML (3 min)
- Ouvrir `salesforce_dq_report.html`
- Pointer le **score global** et expliquer ce qu'il signifie
- Naviguer dans les **tabs par objet** (Account, Contact, Lead, Opportunity)
- Mettre en avant le **radar chart** : "Voici où vous perdez le plus de qualité"

### 3. Live demo SQL (3 min)
Lancer `python 02_sql_dq_checks.py` en direct dans le terminal.
Points à commenter :
- `✗ [RÈGLE MÉTIER] Lead converti sans ConvertedDate` → *"Votre taux de conversion est faux"*
- `✗ [COHÉRENCE]    FK AccountId orphelin dans Contact` → *"Des contacts ne sont rattachés à aucun compte"*
- `✗ [UNICITÉ]      Email Contact = Email Lead` → *"Un même prospect existe en double sous deux objets différents"*
- `✗ [RÈGLE MÉTIER] StageName=Gagné mais IsWon=0` → *"Vos revenus gagnés sont sous-estimés dans le CRM"*

### 4. Impact sur le modèle IA (2 min)
> *"Si on entraîne le modèle de scoring sur ces données telles quelles :*
> - *Les opportunités 'stale' (CloseDate dépassée, encore ouvertes) vont apprendre
>   au modèle qu'une opportunité peut durer indéfiniment → biais de pipeline*
> - *Les doublons Contact/Lead vont créer des features dupliquées → surapprentissage*
> - *Les incohérences StageName/IsWon vont polluer la variable cible → prédictions fausses"*

### 5. Plan de remédiation (1 min)
Pointer le tableau de recommandations dans le rapport HTML :
- 🔴 **Critique** : à corriger avant tout entraînement IA
- 🟠 **Haute** : à adresser dans le premier sprint
- 🟡 **Moyenne** : à planifier dans la roadmap qualité

---

## Ce que ce projet démontre (pour l'entretien)

| Compétence | Comment c'est montré |
|---|---|
| Connaissance Salesforce | 4 objets CRM natifs, picklists exactes, règles métier SF |
| SQL avancé | JOINs inter-tables, GROUP BY, sous-requêtes, règles métier |
| Python Data Quality | Profiling, fuzzy matching, scoring, génération de rapport |
| Dimension DQ | Complétude · Unicité · Validité · Cohérence · Règle métier |
| Impact IA | Lien explicite entre qualité des données et performance du modèle |
| Communication client | Rapport HTML visuel, recommandations priorisées |

---

## Questions probables en entretien + réponses suggérées

**Q : Comment tu connecterais ça au vrai Salesforce ?**
> "Via l'API REST Salesforce ou la librairie `simple_salesforce` en Python.
> On remplace le SQLite par un extract SOQL et tout le reste est identique."

**Q : Et si le volume est beaucoup plus grand (millions de lignes) ?**
> "On bascule les checks SQL sur le DWH (Snowflake, BigQuery).
> Python reste pour l'orchestration et le reporting. On peut aussi
> intégrer Great Expectations pour un framework de checks déclaratif."

**Q : Comment tu priorises les corrections ?**
> "Par impact sur le cas d'usage IA. On corrige d'abord ce qui pollue
> la variable cible du modèle, puis ce qui affecte les features critiques,
> puis le reste en amélioration continue."

**Q : C'est quoi ton framework DQ de référence ?**
> "Les 6 dimensions DAMA : Complétude, Unicité, Validité, Cohérence,
> Exactitude, Temporalité. Ici je me concentre sur les 5 observables
> directement via SQL, sans avoir besoin de source de référence externe."
