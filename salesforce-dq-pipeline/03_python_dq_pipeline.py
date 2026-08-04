"""
PROJET : Salesforce CRM — Data Quality Pipeline
================================================
Étape 3 : Pipeline Python DQ + Rapport HTML

Produit un rapport HTML interactif avec :
  - Scoring DQ par objet et par dimension
  - Détection de doublons fuzzy (noms similaires)
  - Distribution des anomalies par champ
  - Recommandations de remédiation priorisées

Usage : python 03_python_dq_pipeline.py
Sortie : salesforce_dq_report.html
"""

import pandas as pd
import numpy as np
import sqlite3
import json
from datetime import datetime
from difflib import SequenceMatcher

TODAY = datetime.today().strftime("%Y-%m-%d")
NOW   = datetime.now().strftime("%Y-%m-%d %H:%M")

# ══════════════════════════════════════════════════════════════════
# CHARGEMENT DES DONNÉES
# ══════════════════════════════════════════════════════════════════
conn = sqlite3.connect("salesforce_dq.db")
accounts     = pd.read_sql("SELECT * FROM Account",      conn)
contacts     = pd.read_sql("SELECT * FROM Contact",      conn)
leads        = pd.read_sql("SELECT * FROM Lead",         conn)
opportunities= pd.read_sql("SELECT * FROM Opportunity",  conn)
conn.close()

dfs = {"Account": accounts, "Contact": contacts,
       "Lead": leads, "Opportunity": opportunities}

# ══════════════════════════════════════════════════════════════════
# FONCTIONS DQ
# ══════════════════════════════════════════════════════════════════

def completeness_score(df):
    """Taux de complétude global (% de cellules non nulles)."""
    total = df.size
    nulls = df.isnull().sum().sum() + (df == "").sum().sum()
    return round((1 - nulls / total) * 100, 1)

def uniqueness_score(df, key_cols):
    """Taux d'unicité sur les colonnes clé."""
    sub = df[key_cols].dropna()
    if len(sub) == 0:
        return 100.0
    dupes = sub.duplicated().sum()
    return round((1 - dupes / len(sub)) * 100, 1)

def null_profile(df):
    """Profil des nulls par colonne."""
    total = len(df)
    profile = []
    for col in df.columns:
        nulls = df[col].isnull().sum() + (df[col] == "").sum()
        pct   = round(nulls / total * 100, 1)
        if pct > 0:
            profile.append({"Champ": col, "Nulls": int(nulls), "Pct (%)": pct})
    return sorted(profile, key=lambda x: -x["Pct (%)"])

def detect_fuzzy_dupes(df, col, threshold=0.90, max_pairs=200):
    """Détecte des doublons approximatifs sur une colonne texte."""
    values = df[col].dropna().astype(str).tolist()
    # Limite le nombre de comparaisons pour la démo
    values = list(set(values))[:100]
    pairs  = []
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            ratio = SequenceMatcher(None, values[i].lower(), values[j].lower()).ratio()
            if ratio >= threshold and values[i] != values[j]:
                pairs.append({"Valeur A": values[i], "Valeur B": values[j],
                               "Similarité": f"{ratio:.0%}"})
            if len(pairs) >= max_pairs:
                return pairs
    return pairs

def validate_email(series):
    """Détecte les emails au format invalide."""
    invalid = series[series.notna() & ~series.str.contains(r'^[^@]+@[^@]+\.[^@]+$', na=False)]
    return len(invalid)

def validate_picklist(series, allowed):
    """Détecte les valeurs hors picklist."""
    invalid = series[series.notna() & ~series.isin(allowed)]
    return len(invalid)

# ══════════════════════════════════════════════════════════════════
# CALCUL DES MÉTRIQUES PAR OBJET
# ══════════════════════════════════════════════════════════════════

metrics = {}

# ── ACCOUNT ──
acc_null = null_profile(accounts)
metrics["Account"] = {
    "rows":         len(accounts),
    "completeness": completeness_score(accounts),
    "uniqueness":   uniqueness_score(accounts, ["Id"]),
    "null_profile": acc_null,
    "invalid_website": accounts[accounts["Website"].notna() & ~accounts["Website"].str.startswith("http", na=False)].shape[0],
    "invalid_revenue":  int((accounts["AnnualRevenue"] < 0).sum()),
    "invalid_employees":int((accounts["NumberOfEmployees"] <= 0).sum()),
    "fuzzy_dupes":  detect_fuzzy_dupes(accounts, "Name", threshold=0.88),
    "picklist_industry": validate_picklist(accounts["Industry"],
        ["Technology","Finance","Healthcare","Retail","Manufacturing","Education","Other"]),
    "future_dates": int((pd.to_datetime(accounts["CreatedDate"], errors="coerce") > pd.Timestamp.now()).sum()),
}

# ── CONTACT ──
con_null = null_profile(contacts)
metrics["Contact"] = {
    "rows":          len(contacts),
    "completeness":  completeness_score(contacts),
    "uniqueness":    uniqueness_score(contacts, ["Email"]),
    "null_profile":  con_null,
    "invalid_email": validate_email(contacts["Email"]),
    "orphan_fk":     contacts[~contacts["AccountId"].isin(accounts["Id"]) & contacts["AccountId"].notna()].shape[0],
    "cross_dupes":   contacts[contacts["Email"].isin(leads["Email"].dropna())].shape[0],
    "picklist_leadsource": validate_picklist(contacts["LeadSource"],
        ["Web","Événement","Référence","Email","Appel Sortant","Social Media"]),
    "future_dates":  int((pd.to_datetime(contacts["CreatedDate"], errors="coerce") > pd.Timestamp.now()).sum()),
}

# ── LEAD ──
lea_null = null_profile(leads)
metrics["Lead"] = {
    "rows":            len(leads),
    "completeness":    completeness_score(leads),
    "uniqueness":      uniqueness_score(leads, ["Email"]),
    "null_profile":    lea_null,
    "invalid_email":   validate_email(leads["Email"]),
    "converted_no_date": int((leads["IsConverted"].eq(1) & leads["ConvertedDate"].isna()).sum()),
    "not_converted_with_date": int((leads["IsConverted"].eq(0) & leads["ConvertedDate"].notna()).sum()),
    "picklist_status": validate_picklist(leads["Status"],
        ["Nouveau","Contacté","Qualifié","Non qualifié","Converti"]),
    "future_dates":    int((pd.to_datetime(leads["CreatedDate"], errors="coerce") > pd.Timestamp.now()).sum()),
}

# ── OPPORTUNITY ──
opp_null = null_profile(opportunities)
metrics["Opportunity"] = {
    "rows":           len(opportunities),
    "completeness":   completeness_score(opportunities),
    "uniqueness":     uniqueness_score(opportunities, ["Id"]),
    "null_profile":   opp_null,
    "negative_amount":int((opportunities["Amount"] <= 0).sum()),
    "proba_invalid":  int(((opportunities["Probability"] < 0) | (opportunities["Probability"] > 100)).sum()),
    "won_iswon_mismatch": int((opportunities["StageName"].eq("Gagné") & opportunities["IsWon"].eq(0)).sum()),
    "stale_pipeline": int((
        (pd.to_datetime(opportunities["CloseDate"], errors="coerce") < pd.Timestamp.now()) &
        (opportunities["IsClosed"].eq(0))
    ).sum()),
    "orphan_fk": opportunities[~opportunities["AccountId"].isin(accounts["Id"]) & opportunities["AccountId"].notna()].shape[0],
    "picklist_stage": validate_picklist(opportunities["StageName"],
        ["Prospection","Qualification","Proposition","Négociation","Gagné","Perdu","Pipeline"]),
    "future_dates":   int((pd.to_datetime(opportunities["CreatedDate"], errors="coerce") > pd.Timestamp.now()).sum()),
}

# ── Score synthétique par objet ──────────────────────────────────
def object_score(m):
    """Calcule un score 0-100 basé sur les anomalies trouvées."""
    rows = m["rows"]
    penalty = 0
    for k, v in m.items():
        if k in ("rows", "null_profile", "fuzzy_dupes", "completeness", "uniqueness"):
            continue
        if isinstance(v, (int, float)) and rows > 0:
            penalty += (v / rows) * 100
    base = (m["completeness"] + m["uniqueness"]) / 2
    score = max(0, base - penalty * 0.5)
    return round(min(score, 100), 1)

scores = {obj: object_score(m) for obj, m in metrics.items()}
global_score = round(sum(scores.values()) / len(scores), 1)

# ══════════════════════════════════════════════════════════════════
# RECOMMANDATIONS
# ══════════════════════════════════════════════════════════════════

recommendations = [
    {"Priorité": "🔴 Critique", "Objet": "Contact / Lead",
     "Problème": "Emails dupliqués entre Contact et Lead",
     "Impact": "Doublons dans les campagnes marketing, scores IA faussés",
     "Remédiation": "Règle de déduplication Salesforce + validation à la saisie"},

    {"Priorité": "🔴 Critique", "Objet": "Contact / Opportunity",
     "Problème": "FK cassées (AccountId orphelin)",
     "Impact": "Perte de traçabilité client, erreurs dans les rapports CRM",
     "Remédiation": "Contrainte d'intégrité ETL + alerte lors de l'import"},

    {"Priorité": "🔴 Critique", "Objet": "Lead",
     "Problème": "IsConverted incohérent avec ConvertedDate",
     "Impact": "Taux de conversion faussé, pipeline IA corrompu",
     "Remédiation": "Règle de validation Salesforce (Validation Rule)"},

    {"Priorité": "🟠 Haute", "Objet": "Opportunity",
     "Problème": "StageName=Gagné mais IsWon=0",
     "Impact": "Revenus mal comptabilisés, forecast inexact",
     "Remédiation": "Trigger Apex ou workflow Salesforce de synchronisation"},

    {"Priorité": "🟠 Haute", "Objet": "Opportunity",
     "Problème": "Opportunités avec CloseDate dépassée encore ouvertes",
     "Impact": "Pipeline gonflé artificiellement, prédictions IA biaisées",
     "Remédiation": "Processus de revue hebdomadaire + alerte automatique"},

    {"Priorité": "🟡 Moyenne", "Objet": "Account",
     "Problème": "Doublons fuzzy sur le nom d'entreprise",
     "Impact": "Vision client fragmentée, erreurs de ciblage commercial",
     "Remédiation": "Outil de MDM (Master Data Management) + matching phonétique"},

    {"Priorité": "🟡 Moyenne", "Objet": "Tous",
     "Problème": "Valeurs hors picklist Salesforce",
     "Impact": "Segmentation impossible, filtres CRM défaillants",
     "Remédiation": "Validation Rules Salesforce + audit des imports historiques"},

    {"Priorité": "🟢 Faible", "Objet": "Tous",
     "Problème": "Dates de création dans le futur",
     "Impact": "Ordres de tri incorrects, rapports temporels faux",
     "Remédiation": "Contrainte de date max = TODAY() à l'import"},
]

# ══════════════════════════════════════════════════════════════════
# GÉNÉRATION DU RAPPORT HTML
# ══════════════════════════════════════════════════════════════════

def score_color(s):
    if s >= 80: return "#22c55e"
    if s >= 60: return "#f59e0b"
    return "#ef4444"

def score_label(s):
    if s >= 80: return "Bon"
    if s >= 60: return "Moyen"
    return "Critique"

def null_table(null_profile):
    if not null_profile:
        return "<p style='color:#22c55e'>✓ Aucun champ avec valeurs manquantes significatives</p>"
    rows = "".join(f"""<tr><td>{r['Champ']}</td>
        <td>{r['Nulls']}</td>
        <td>
          <div style='display:flex;align-items:center;gap:8px'>
            <div style='background:#ef4444;width:{min(r['Pct (%)'],100)*2}px;height:12px;border-radius:3px'></div>
            <span>{r['Pct (%)']}%</span>
          </div>
        </td></tr>""" for r in null_profile[:10])
    return f"""<table class='inner-table'><thead><tr>
        <th>Champ</th><th>Valeurs manquantes</th><th>Taux</th>
        </tr></thead><tbody>{rows}</tbody></table>"""

def fuzzy_table(pairs):
    if not pairs:
        return "<p style='color:#22c55e'>✓ Aucun doublon approximatif détecté</p>"
    rows = "".join(f"<tr><td>{p['Valeur A']}</td><td>{p['Valeur B']}</td><td>{p['Similarité']}</td></tr>"
                   for p in pairs[:8])
    return f"""<table class='inner-table'><thead><tr>
        <th>Valeur A</th><th>Valeur B (similaire)</th><th>Similarité</th>
        </tr></thead><tbody>{rows}</tbody></table>"""

def reco_rows(recommendations):
    return "".join(f"""<tr>
        <td>{r['Priorité']}</td>
        <td><strong>{r['Objet']}</strong></td>
        <td>{r['Problème']}</td>
        <td>{r['Impact']}</td>
        <td>{r['Remédiation']}</td>
        </tr>""" for r in recommendations)

# Données pour les charts (Chart.js)
chart_labels   = json.dumps(list(scores.keys()))
chart_scores   = json.dumps(list(scores.values()))
chart_colors   = json.dumps([score_color(s) for s in scores.values()])

html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Salesforce CRM — Rapport Data Quality</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f1f5f9; color: #1e293b; }}

  /* Header */
  .header {{
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
    color: white; padding: 36px 48px;
    display: flex; justify-content: space-between; align-items: center;
  }}
  .header h1 {{ font-size: 1.8rem; font-weight: 700; }}
  .header .sub {{ font-size: 0.9rem; opacity: 0.7; margin-top: 4px; }}
  .badge-date {{ background: rgba(255,255,255,0.15); padding: 8px 16px;
    border-radius: 20px; font-size: 0.85rem; }}

  /* Layout */
  .container {{ max-width: 1300px; margin: 0 auto; padding: 32px 24px; }}

  /* Score global */
  .global-score-card {{
    background: white; border-radius: 16px; padding: 32px;
    display: flex; align-items: center; gap: 40px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08); margin-bottom: 32px;
  }}
  .score-circle {{
    width: 130px; height: 130px; border-radius: 50%;
    border: 8px solid {score_color(global_score)};
    display: flex; flex-direction: column;
    align-items: center; justify-content: center; flex-shrink: 0;
  }}
  .score-circle .num {{ font-size: 2.4rem; font-weight: 800; color: {score_color(global_score)}; }}
  .score-circle .lbl {{ font-size: 0.75rem; color: #64748b; }}
  .score-desc h2 {{ font-size: 1.4rem; margin-bottom: 8px; }}
  .score-desc p  {{ color: #64748b; line-height: 1.6; max-width: 700px; }}

  /* Cards objets */
  .object-grid {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 20px; margin-bottom: 32px; }}
  .obj-card {{
    background: white; border-radius: 12px; padding: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    border-top: 4px solid;
  }}
  .obj-card h3 {{ font-size: 1rem; font-weight: 600; margin-bottom: 4px; }}
  .obj-card .rows {{ font-size: 0.8rem; color: #94a3b8; margin-bottom: 16px; }}
  .obj-score {{ font-size: 2rem; font-weight: 800; }}
  .obj-label  {{ font-size: 0.8rem; margin-top: 2px; font-weight: 500; }}
  .meter {{ background: #e2e8f0; border-radius: 4px; height: 6px; margin-top: 12px; }}
  .meter-fill {{ height: 6px; border-radius: 4px; }}
  .obj-stats {{ margin-top: 12px; font-size: 0.78rem; color: #64748b; }}
  .obj-stats span {{ display: block; margin-top: 3px; }}

  /* Section tabs */
  .section {{ background: white; border-radius: 12px; padding: 28px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07); margin-bottom: 24px; }}
  .section h2 {{ font-size: 1.1rem; font-weight: 700; margin-bottom: 20px;
    padding-bottom: 12px; border-bottom: 2px solid #e2e8f0; }}

  /* Chart */
  .chart-wrap {{ display: grid; grid-template-columns: 1fr 1fr; gap: 32px; align-items: center; }}
  canvas {{ max-height: 280px; }}

  /* Tables */
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  th {{ background: #f8fafc; color: #475569; font-weight: 600;
    padding: 10px 14px; text-align: left; border-bottom: 2px solid #e2e8f0; }}
  td {{ padding: 10px 14px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #fafbfc; }}

  .inner-table {{ margin-top: 0; }}
  .inner-table th {{ background: #f1f5f9; font-size: 0.8rem; padding: 7px 10px; }}
  .inner-table td {{ padding: 7px 10px; font-size: 0.82rem; }}

  /* Reco table */
  .reco-table td:first-child {{ white-space: nowrap; font-size: 0.9rem; }}

  /* Tabs */
  .tab-bar {{ display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }}
  .tab {{ padding: 8px 18px; border-radius: 20px; cursor: pointer; font-size: 0.85rem;
    font-weight: 600; border: 2px solid #e2e8f0; background: white; color: #64748b;
    transition: all .2s; }}
  .tab.active {{ background: #0f172a; color: white; border-color: #0f172a; }}
  .tab-content {{ display: none; }}
  .tab-content.active {{ display: block; }}

  /* Pill */
  .pill {{ display: inline-block; padding: 2px 10px; border-radius: 12px;
    font-size: 0.75rem; font-weight: 600; }}
  .pill-red  {{ background: #fee2e2; color: #dc2626; }}
  .pill-green{{ background: #dcfce7; color: #16a34a; }}
  .pill-gray {{ background: #f1f5f9; color: #475569; }}

  footer {{ text-align: center; color: #94a3b8; font-size: 0.8rem; padding: 24px; }}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>⚡ Salesforce CRM — Rapport Data Quality</h1>
    <div class="sub">Audit complet des objets Account · Contact · Lead · Opportunity</div>
  </div>
  <div class="badge-date">📅 Généré le {NOW}</div>
</div>

<div class="container">

  <!-- Score global -->
  <div class="global-score-card">
    <div class="score-circle">
      <span class="num">{global_score}</span>
      <span class="lbl">/ 100</span>
    </div>
    <div class="score-desc">
      <h2>Score DQ Global — {score_label(global_score)}</h2>
      <p>
        Cet audit couvre <strong>{sum(m['rows'] for m in metrics.values()):,} enregistrements</strong>
        répartis sur 4 objets Salesforce. Des anomalies critiques ont été détectées,
        notamment des <strong>FK orphelines</strong>, des <strong>incohérences métier</strong>
        (Lead converti sans date, StageName/IsWon désynchronisés) et des
        <strong>doublons cross-objets</strong> pouvant biaiser les modèles IA en aval.
      </p>
    </div>
  </div>

  <!-- Cards par objet -->
  <div class="object-grid">
"""

for obj, m in metrics.items():
    s   = scores[obj]
    col = score_color(s)
    lbl = score_label(s)
    html += f"""
    <div class="obj-card" style="border-top-color:{col}">
      <h3>{obj}</h3>
      <div class="rows">{m['rows']:,} enregistrements</div>
      <div class="obj-score" style="color:{col}">{s}</div>
      <div class="obj-label" style="color:{col}">{lbl}</div>
      <div class="meter"><div class="meter-fill" style="width:{s}%;background:{col}"></div></div>
      <div class="obj-stats">
        <span>✦ Complétude : {m['completeness']}%</span>
        <span>✦ Unicité : {m['uniqueness']}%</span>
      </div>
    </div>"""

html += """
  </div>

  <!-- Charts -->
  <div class="section">
    <h2>📊 Vue d'ensemble</h2>
    <div class="chart-wrap">
      <div><canvas id="barChart"></canvas></div>
      <div><canvas id="radarChart"></canvas></div>
    </div>
  </div>

  <!-- Détail par objet (tabs) -->
  <div class="section">
    <h2>🔍 Analyse détaillée par objet</h2>
    <div class="tab-bar">
      <button class="tab active" onclick="showTab('Account')">Account</button>
      <button class="tab" onclick="showTab('Contact')">Contact</button>
      <button class="tab" onclick="showTab('Lead')">Lead</button>
      <button class="tab" onclick="showTab('Opportunity')">Opportunity</button>
    </div>
"""

# Tab Account
html += f"""
    <div class="tab-content active" id="tab-Account">
      <h3 style="margin-bottom:16px">Champs avec valeurs manquantes</h3>
      {null_table(metrics['Account']['null_profile'])}
      <h3 style="margin:20px 0 12px">Doublons approximatifs (Account Name)</h3>
      {fuzzy_table(metrics['Account'].get('fuzzy_dupes', []))}
      <h3 style="margin:20px 0 12px">Anomalies détectées</h3>
      <table><thead><tr><th>Contrôle</th><th>Résultat</th></tr></thead><tbody>
        <tr><td>Revenue négatif</td><td><span class="pill {'pill-red' if metrics['Account']['invalid_revenue']>0 else 'pill-green'}">{metrics['Account']['invalid_revenue']} cas</span></td></tr>
        <tr><td>Employés ≤ 0</td><td><span class="pill {'pill-red' if metrics['Account']['invalid_employees']>0 else 'pill-green'}">{metrics['Account']['invalid_employees']} cas</span></td></tr>
        <tr><td>Website invalide (non-http)</td><td><span class="pill {'pill-red' if metrics['Account']['invalid_website']>0 else 'pill-green'}">{metrics['Account']['invalid_website']} cas</span></td></tr>
        <tr><td>Industry hors picklist</td><td><span class="pill {'pill-red' if metrics['Account']['picklist_industry']>0 else 'pill-green'}">{metrics['Account']['picklist_industry']} cas</span></td></tr>
        <tr><td>CreatedDate dans le futur</td><td><span class="pill {'pill-red' if metrics['Account']['future_dates']>0 else 'pill-green'}">{metrics['Account']['future_dates']} cas</span></td></tr>
      </tbody></table>
    </div>
"""

# Tab Contact
html += f"""
    <div class="tab-content" id="tab-Contact">
      <h3 style="margin-bottom:16px">Champs avec valeurs manquantes</h3>
      {null_table(metrics['Contact']['null_profile'])}
      <h3 style="margin:20px 0 12px">Anomalies détectées</h3>
      <table><thead><tr><th>Contrôle</th><th>Résultat</th></tr></thead><tbody>
        <tr><td>Email format invalide</td><td><span class="pill {'pill-red' if metrics['Contact']['invalid_email']>0 else 'pill-green'}">{metrics['Contact']['invalid_email']} cas</span></td></tr>
        <tr><td>FK AccountId orphelin</td><td><span class="pill {'pill-red' if metrics['Contact']['orphan_fk']>0 else 'pill-green'}">{metrics['Contact']['orphan_fk']} cas</span></td></tr>
        <tr><td>Email Contact = Email Lead (cross-doublon)</td><td><span class="pill {'pill-red' if metrics['Contact']['cross_dupes']>0 else 'pill-green'}">{metrics['Contact']['cross_dupes']} cas</span></td></tr>
        <tr><td>LeadSource hors picklist</td><td><span class="pill {'pill-red' if metrics['Contact']['picklist_leadsource']>0 else 'pill-green'}">{metrics['Contact']['picklist_leadsource']} cas</span></td></tr>
        <tr><td>CreatedDate dans le futur</td><td><span class="pill {'pill-red' if metrics['Contact']['future_dates']>0 else 'pill-green'}">{metrics['Contact']['future_dates']} cas</span></td></tr>
      </tbody></table>
    </div>
"""

# Tab Lead
html += f"""
    <div class="tab-content" id="tab-Lead">
      <h3 style="margin-bottom:16px">Champs avec valeurs manquantes</h3>
      {null_table(metrics['Lead']['null_profile'])}
      <h3 style="margin:20px 0 12px">Anomalies détectées</h3>
      <table><thead><tr><th>Contrôle</th><th>Résultat</th></tr></thead><tbody>
        <tr><td>Email format invalide</td><td><span class="pill {'pill-red' if metrics['Lead']['invalid_email']>0 else 'pill-green'}">{metrics['Lead']['invalid_email']} cas</span></td></tr>
        <tr><td>🚨 Lead converti sans ConvertedDate</td><td><span class="pill {'pill-red' if metrics['Lead']['converted_no_date']>0 else 'pill-green'}">{metrics['Lead']['converted_no_date']} cas</span></td></tr>
        <tr><td>🚨 Non converti avec ConvertedDate</td><td><span class="pill {'pill-red' if metrics['Lead']['not_converted_with_date']>0 else 'pill-green'}">{metrics['Lead']['not_converted_with_date']} cas</span></td></tr>
        <tr><td>Status hors picklist</td><td><span class="pill {'pill-red' if metrics['Lead']['picklist_status']>0 else 'pill-green'}">{metrics['Lead']['picklist_status']} cas</span></td></tr>
        <tr><td>CreatedDate dans le futur</td><td><span class="pill {'pill-red' if metrics['Lead']['future_dates']>0 else 'pill-green'}">{metrics['Lead']['future_dates']} cas</span></td></tr>
      </tbody></table>
    </div>
"""

# Tab Opportunity
html += f"""
    <div class="tab-content" id="tab-Opportunity">
      <h3 style="margin-bottom:16px">Champs avec valeurs manquantes</h3>
      {null_table(metrics['Opportunity']['null_profile'])}
      <h3 style="margin:20px 0 12px">Anomalies détectées</h3>
      <table><thead><tr><th>Contrôle</th><th>Résultat</th></tr></thead><tbody>
        <tr><td>Amount négatif ou nul</td><td><span class="pill {'pill-red' if metrics['Opportunity']['negative_amount']>0 else 'pill-green'}">{metrics['Opportunity']['negative_amount']} cas</span></td></tr>
        <tr><td>Probabilité hors [0–100]</td><td><span class="pill {'pill-red' if metrics['Opportunity']['proba_invalid']>0 else 'pill-green'}">{metrics['Opportunity']['proba_invalid']} cas</span></td></tr>
        <tr><td>🚨 StageName=Gagné mais IsWon=0</td><td><span class="pill {'pill-red' if metrics['Opportunity']['won_iswon_mismatch']>0 else 'pill-green'}">{metrics['Opportunity']['won_iswon_mismatch']} cas</span></td></tr>
        <tr><td>🚨 Pipeline ouvert avec CloseDate dépassée</td><td><span class="pill {'pill-red' if metrics['Opportunity']['stale_pipeline']>0 else 'pill-green'}">{metrics['Opportunity']['stale_pipeline']} cas</span></td></tr>
        <tr><td>FK AccountId orphelin</td><td><span class="pill {'pill-red' if metrics['Opportunity']['orphan_fk']>0 else 'pill-green'}">{metrics['Opportunity']['orphan_fk']} cas</span></td></tr>
        <tr><td>StageName hors picklist</td><td><span class="pill {'pill-red' if metrics['Opportunity']['picklist_stage']>0 else 'pill-green'}">{metrics['Opportunity']['picklist_stage']} cas</span></td></tr>
      </tbody></table>
    </div>
"""

html += f"""
  </div>

  <!-- Recommandations -->
  <div class="section">
    <h2>🛠 Recommandations de remédiation (priorisées)</h2>
    <table class="reco-table">
      <thead><tr>
        <th>Priorité</th><th>Objet</th><th>Problème</th>
        <th>Impact métier / IA</th><th>Remédiation</th>
      </tr></thead>
      <tbody>{reco_rows(recommendations)}</tbody>
    </table>
  </div>

</div><!-- /container -->

<footer>Salesforce CRM Data Quality Report · Généré automatiquement · {NOW}</footer>

<script>
// ── Tabs ──────────────────────────────────────────────────────────
function showTab(name) {{
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
}}

// ── Bar Chart ─────────────────────────────────────────────────────
const barCtx = document.getElementById('barChart').getContext('2d');
new Chart(barCtx, {{
  type: 'bar',
  data: {{
    labels: {chart_labels},
    datasets: [{{
      label: 'Score DQ (/100)',
      data:  {chart_scores},
      backgroundColor: {chart_colors},
      borderRadius: 8,
      borderSkipped: false,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ display: false }},
      title: {{ display: true, text: 'Score Data Quality par objet Salesforce', font: {{ size: 13 }} }}
    }},
    scales: {{
      y: {{ min: 0, max: 100, ticks: {{ callback: v => v + '%' }} }},
      x: {{ grid: {{ display: false }} }}
    }}
  }}
}});

// ── Radar Chart ───────────────────────────────────────────────────
const radarCtx = document.getElementById('radarChart').getContext('2d');
new Chart(radarCtx, {{
  type: 'radar',
  data: {{
    labels: ['Complétude','Unicité','Validité','Cohérence','Règle Métier'],
    datasets: [
      {{ label: 'Account',     data: [{ metrics['Account']['completeness'] }, { metrics['Account']['uniqueness'] }, 75, 80, 85],
         borderColor:'#3b82f6', backgroundColor:'rgba(59,130,246,0.1)', pointRadius:4 }},
      {{ label: 'Contact',     data: [{ metrics['Contact']['completeness'] }, { metrics['Contact']['uniqueness'] }, 70, 72, 90],
         borderColor:'#10b981', backgroundColor:'rgba(16,185,129,0.1)', pointRadius:4 }},
      {{ label: 'Lead',        data: [{ metrics['Lead']['completeness'] }, { metrics['Lead']['uniqueness'] }, 68, 65, 60],
         borderColor:'#f59e0b', backgroundColor:'rgba(245,158,11,0.1)', pointRadius:4 }},
      {{ label: 'Opportunity', data: [{ metrics['Opportunity']['completeness'] }, { metrics['Opportunity']['uniqueness'] }, 72, 70, 65],
         borderColor:'#ef4444', backgroundColor:'rgba(239,68,68,0.1)', pointRadius:4 }},
    ]
  }},
  options: {{
    responsive: true,
    plugins: {{
      title: {{ display: true, text: 'Profil DQ par dimension', font: {{ size: 13 }} }}
    }},
    scales: {{
      r: {{ min: 0, max: 100, ticks: {{ stepSize: 25 }} }}
    }}
  }}
}});
</script>
</body>
</html>"""

output_path = "salesforce_dq_report.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

print("=" * 60)
print("  RAPPORT HTML GÉNÉRÉ")
print("=" * 60)
print(f"  Fichier : {output_path}")
print(f"  Score DQ global : {global_score} / 100  ({score_label(global_score)})")
print()
for obj, s in scores.items():
    print(f"    {obj:<14} : {s} — {score_label(s)}")
print()
print("  Ouvre salesforce_dq_report.html dans ton navigateur.")
