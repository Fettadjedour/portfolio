"""
PROJET : Salesforce CRM — Data Quality Pipeline
================================================
Étape 2 : Checks SQL de Data Quality

Couvre les 5 dimensions DQ sur les 4 objets Salesforce :
  COMPLÉTUDE  · UNICITÉ  · VALIDITÉ  · COHÉRENCE  · RÈGLE MÉTIER

Reproduit ce qu'on déploierait sur un DWH (Snowflake, BigQuery…)
après extraction Salesforce via API ou ETL.

Usage : python 02_sql_dq_checks.py
"""

import sqlite3
import pandas as pd
from datetime import datetime

conn = sqlite3.connect("salesforce_dq.db")
TODAY = datetime.today().strftime("%Y-%m-%d")

# ── Terminal colors ────────────────────────────────────────────────
GREEN  = "\033[92m"; RED    = "\033[91m"
YELLOW = "\033[93m"; BLUE   = "\033[94m"
BOLD   = "\033[1m";  RESET  = "\033[0m"

results = []

def check(name, dimension, obj, sql, expected_zero=True):
    df    = pd.read_sql_query(sql, conn)
    count = int(df.iloc[0, 0])
    passed = (count == 0) if expected_zero else True
    status = "PASS" if passed else "FAIL"
    icon   = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
    col    = GREEN if passed else RED
    print(f"  {icon} [{dimension:<15}] [{obj:<12}] {name:<55} → {col}{count}{RESET}")
    results.append({"Objet": obj, "Dimension": dimension, "Check": name,
                    "Anomalies": count, "Statut": status})


# ══════════════════════════════════════════════════════════════════
print(f"\n{BOLD}{BLUE}{'═'*80}{RESET}")
print(f"{BOLD}{BLUE}  SALESFORCE DATA QUALITY — Checks SQL{RESET}")
print(f"{BOLD}{BLUE}{'═'*80}{RESET}\n")

# ─────────────────────────────────────────────────────────────────
# ACCOUNT
# ─────────────────────────────────────────────────────────────────
print(f"\n{BOLD}── ACCOUNT ──{RESET}")

check("Nom nul ou vide",               "COMPLÉTUDE",   "Account",
      "SELECT COUNT(*) FROM Account WHERE Name IS NULL OR TRIM(Name) = ''")

check("BillingCountry nul",            "COMPLÉTUDE",   "Account",
      "SELECT COUNT(*) FROM Account WHERE BillingCountry IS NULL")

check("OwnerId nul",                   "COMPLÉTUDE",   "Account",
      "SELECT COUNT(*) FROM Account WHERE OwnerId IS NULL")

check("Phone nul",                     "COMPLÉTUDE",   "Account",
      "SELECT COUNT(*) FROM Account WHERE Phone IS NULL")

check("Doublons Id",                   "UNICITÉ",      "Account",
      """SELECT COUNT(*) FROM (
           SELECT Id, COUNT(*) n FROM Account GROUP BY Id HAVING n > 1)""")

check("Doublons Nom + Pays (compte en double probable)", "UNICITÉ", "Account",
      """SELECT COUNT(*) FROM (
           SELECT Name, BillingCountry, COUNT(*) n FROM Account
           WHERE Name IS NOT NULL AND BillingCountry IS NOT NULL
           GROUP BY Name, BillingCountry HAVING n > 1)""")

check("AnnualRevenue négatif",         "VALIDITÉ",     "Account",
      "SELECT COUNT(*) FROM Account WHERE AnnualRevenue < 0")

check("NumberOfEmployees <= 0",        "VALIDITÉ",     "Account",
      "SELECT COUNT(*) FROM Account WHERE NumberOfEmployees <= 0")

check("Industry hors picklist Salesforce", "VALIDITÉ", "Account",
      """SELECT COUNT(*) FROM Account
         WHERE Industry NOT IN
           ('Technology','Finance','Healthcare','Retail','Manufacturing','Education','Other')
         AND Industry IS NOT NULL""")

check("Type hors picklist",            "VALIDITÉ",     "Account",
      """SELECT COUNT(*) FROM Account
         WHERE Type NOT IN ('Customer','Prospect','Partner','Competitor')
         AND Type IS NOT NULL""")

check("Website au format invalide",    "VALIDITÉ",     "Account",
      """SELECT COUNT(*) FROM Account
         WHERE Website IS NOT NULL
         AND Website NOT LIKE 'http%'""")

check("CreatedDate dans le futur",     "COHÉRENCE",    "Account",
      f"SELECT COUNT(*) FROM Account WHERE CreatedDate > '{TODAY}'")

check("LastModifiedDate < CreatedDate","COHÉRENCE",    "Account",
      "SELECT COUNT(*) FROM Account WHERE LastModifiedDate < CreatedDate")


# ─────────────────────────────────────────────────────────────────
# CONTACT
# ─────────────────────────────────────────────────────────────────
print(f"\n{BOLD}── CONTACT ──{RESET}")

check("LastName nul",                  "COMPLÉTUDE",   "Contact",
      "SELECT COUNT(*) FROM Contact WHERE LastName IS NULL OR TRIM(LastName) = ''")

check("FirstName nul",                 "COMPLÉTUDE",   "Contact",
      "SELECT COUNT(*) FROM Contact WHERE FirstName IS NULL")

check("Email nul",                     "COMPLÉTUDE",   "Contact",
      "SELECT COUNT(*) FROM Contact WHERE Email IS NULL")

check("AccountId nul (contact orphelin)", "COMPLÉTUDE","Contact",
      "SELECT COUNT(*) FROM Contact WHERE AccountId IS NULL")

check("Doublons Email",                "UNICITÉ",      "Contact",
      """SELECT COUNT(*) FROM (
           SELECT Email, COUNT(*) n FROM Contact
           WHERE Email IS NOT NULL GROUP BY Email HAVING n > 1)""")

check("Doublons Prénom+Nom+Entreprise","UNICITÉ",      "Contact",
      """SELECT COUNT(*) FROM (
           SELECT FirstName, LastName, AccountId, COUNT(*) n FROM Contact
           WHERE FirstName IS NOT NULL AND LastName IS NOT NULL
           GROUP BY FirstName, LastName, AccountId HAVING n > 1)""")

check("Email format invalide",         "VALIDITÉ",     "Contact",
      """SELECT COUNT(*) FROM Contact
         WHERE Email IS NOT NULL
         AND (Email NOT LIKE '%@%.%' OR Email LIKE '%@@%')""")

check("Phone au format suspect (<6 chars)", "VALIDITÉ","Contact",
      "SELECT COUNT(*) FROM Contact WHERE Phone IS NOT NULL AND LENGTH(REPLACE(Phone,' ','')) < 6")

check("LeadSource hors picklist",      "VALIDITÉ",     "Contact",
      """SELECT COUNT(*) FROM Contact
         WHERE LeadSource IS NOT NULL
         AND LeadSource NOT IN
           ('Web','Événement','Référence','Email','Appel Sortant','Social Media')""")

check("AccountId inexistant dans Account (FK cassée)", "COHÉRENCE", "Contact",
      """SELECT COUNT(*) FROM Contact c
         LEFT JOIN Account a ON c.AccountId = a.Id
         WHERE c.AccountId IS NOT NULL AND a.Id IS NULL""")

check("CreatedDate dans le futur",     "COHÉRENCE",    "Contact",
      f"SELECT COUNT(*) FROM Contact WHERE CreatedDate > '{TODAY}'")

check("Email Contact = Email Lead (doublon cross-objet)", "UNICITÉ", "Contact",
      """SELECT COUNT(*) FROM Contact c
         INNER JOIN Lead l ON c.Email = l.Email
         WHERE c.Email IS NOT NULL""",
      expected_zero=False)


# ─────────────────────────────────────────────────────────────────
# LEAD
# ─────────────────────────────────────────────────────────────────
print(f"\n{BOLD}── LEAD ──{RESET}")

check("LastName nul",                  "COMPLÉTUDE",   "Lead",
      "SELECT COUNT(*) FROM Lead WHERE LastName IS NULL OR TRIM(LastName) = ''")

check("Email nul",                     "COMPLÉTUDE",   "Lead",
      "SELECT COUNT(*) FROM Lead WHERE Email IS NULL")

check("Company nul",                   "COMPLÉTUDE",   "Lead",
      "SELECT COUNT(*) FROM Lead WHERE Company IS NULL OR TRIM(Company) = ''")

check("Status nul",                    "COMPLÉTUDE",   "Lead",
      "SELECT COUNT(*) FROM Lead WHERE Status IS NULL")

check("Doublons Email",                "UNICITÉ",      "Lead",
      """SELECT COUNT(*) FROM (
           SELECT Email, COUNT(*) n FROM Lead
           WHERE Email IS NOT NULL GROUP BY Email HAVING n > 1)""")

check("Email format invalide",         "VALIDITÉ",     "Lead",
      """SELECT COUNT(*) FROM Lead
         WHERE Email IS NOT NULL
         AND Email NOT LIKE '%@%.%'""")

check("AnnualRevenue négatif",         "VALIDITÉ",     "Lead",
      "SELECT COUNT(*) FROM Lead WHERE AnnualRevenue < 0")

check("Status hors picklist",          "VALIDITÉ",     "Lead",
      """SELECT COUNT(*) FROM Lead
         WHERE Status NOT IN
           ('Nouveau','Contacté','Qualifié','Non qualifié','Converti')
         AND Status IS NOT NULL""")

check("Country hors référentiel",      "VALIDITÉ",     "Lead",
      """SELECT COUNT(*) FROM Lead
         WHERE Country NOT IN
           ('France','Belgique','Suisse','Luxembourg','Allemagne','Espagne','Italie')
         AND Country IS NOT NULL""")

# Règle métier : Lead IsConverted=1 doit avoir ConvertedDate
check("Lead converti sans ConvertedDate", "RÈGLE MÉTIER", "Lead",
      "SELECT COUNT(*) FROM Lead WHERE IsConverted = 1 AND ConvertedDate IS NULL")

# Règle métier : Lead non converti ne doit PAS avoir ConvertedDate
check("Lead non converti avec ConvertedDate", "RÈGLE MÉTIER", "Lead",
      "SELECT COUNT(*) FROM Lead WHERE IsConverted = 0 AND ConvertedDate IS NOT NULL")

check("CreatedDate dans le futur",     "COHÉRENCE",    "Lead",
      f"SELECT COUNT(*) FROM Lead WHERE CreatedDate > '{TODAY}'")


# ─────────────────────────────────────────────────────────────────
# OPPORTUNITY
# ─────────────────────────────────────────────────────────────────
print(f"\n{BOLD}── OPPORTUNITY ──{RESET}")

check("Name nul",                      "COMPLÉTUDE",   "Opportunity",
      "SELECT COUNT(*) FROM Opportunity WHERE Name IS NULL OR TRIM(Name) = ''")

check("Amount nul",                    "COMPLÉTUDE",   "Opportunity",
      "SELECT COUNT(*) FROM Opportunity WHERE Amount IS NULL")

check("CloseDate nulle",               "COMPLÉTUDE",   "Opportunity",
      "SELECT COUNT(*) FROM Opportunity WHERE CloseDate IS NULL")

check("StageName nul",                 "COMPLÉTUDE",   "Opportunity",
      "SELECT COUNT(*) FROM Opportunity WHERE StageName IS NULL OR TRIM(StageName) = ''")

check("Doublons Id",                   "UNICITÉ",      "Opportunity",
      """SELECT COUNT(*) FROM (
           SELECT Id, COUNT(*) n FROM Opportunity GROUP BY Id HAVING n > 1)""")

check("Amount négatif ou nul",         "VALIDITÉ",     "Opportunity",
      "SELECT COUNT(*) FROM Opportunity WHERE Amount <= 0")

check("Probability hors [0–100]",      "VALIDITÉ",     "Opportunity",
      "SELECT COUNT(*) FROM Opportunity WHERE Probability < 0 OR Probability > 100")

check("StageName hors picklist",       "VALIDITÉ",     "Opportunity",
      """SELECT COUNT(*) FROM Opportunity
         WHERE StageName NOT IN
           ('Prospection','Qualification','Proposition','Négociation','Gagné','Perdu','Pipeline')
         AND StageName IS NOT NULL""")

check("ForecastCategory hors picklist","VALIDITÉ",     "Opportunity",
      """SELECT COUNT(*) FROM Opportunity
         WHERE ForecastCategory NOT IN
           ('Pipeline','BestCase','Commit','Closed','Omitted')
         AND ForecastCategory IS NOT NULL""")

# Règle métier : StageName=Gagné doit avoir IsWon=1
check("StageName=Gagné mais IsWon=0",  "RÈGLE MÉTIER", "Opportunity",
      "SELECT COUNT(*) FROM Opportunity WHERE StageName = 'Gagné' AND IsWon = 0")

# Règle métier : Probability=100 mais pas en étape Gagné
check("Probability=100 mais pas Gagné","RÈGLE MÉTIER", "Opportunity",
      "SELECT COUNT(*) FROM Opportunity WHERE Probability = 100 AND StageName != 'Gagné'")

# Règle métier : CloseDate passée mais encore en pipeline ouvert
check("CloseDate dépassée, opportunité toujours ouverte", "RÈGLE MÉTIER", "Opportunity",
      f"""SELECT COUNT(*) FROM Opportunity
          WHERE CloseDate < '{TODAY}'
          AND IsClosed = 0""")

check("AccountId inexistant dans Account", "COHÉRENCE", "Opportunity",
      """SELECT COUNT(*) FROM Opportunity o
         LEFT JOIN Account a ON o.AccountId = a.Id
         WHERE o.AccountId IS NOT NULL AND a.Id IS NULL""")

check("CreatedDate dans le futur",     "COHÉRENCE",    "Opportunity",
      f"SELECT COUNT(*) FROM Opportunity WHERE CreatedDate > '{TODAY}'")


# ══════════════════════════════════════════════════════════════════
# SCORING GLOBAL
# ══════════════════════════════════════════════════════════════════
print(f"\n{BOLD}{BLUE}{'═'*80}{RESET}")
print(f"{BOLD}{BLUE}  SCORE GLOBAL DATA QUALITY — SALESFORCE CRM{RESET}")
print(f"{BOLD}{BLUE}{'═'*80}{RESET}\n")

df = pd.DataFrame(results)
total  = len(df)
passed = df["Statut"].eq("PASS").sum()
failed = df["Statut"].eq("FAIL").sum()
score  = round(passed / total * 100, 1)

col = GREEN if score >= 80 else (YELLOW if score >= 60 else RED)
print(f"  Total checks     : {total}")
print(f"  {GREEN}✓ Passés{RESET}         : {passed}")
print(f"  {RED}✗ Échoués{RESET}        : {failed}")
print(f"  {col}{BOLD}Score DQ global  : {score} / 100{RESET}")

print(f"\n  Par objet Salesforce :")
for obj, grp in df.groupby("Objet"):
    p = grp["Statut"].eq("PASS").sum()
    t = len(grp)
    s = round(p / t * 100)
    c = GREEN if s >= 80 else (YELLOW if s >= 60 else RED)
    bar = "█" * int(s / 5) + "░" * (20 - int(s / 5))
    print(f"    {obj:<14} [{bar}] {c}{s}%{RESET}  ({p}/{t})")

print(f"\n  Par dimension DQ :")
for dim, grp in df.groupby("Dimension"):
    p = grp["Statut"].eq("PASS").sum()
    t = len(grp)
    s = round(p / t * 100)
    c = GREEN if s >= 80 else (YELLOW if s >= 60 else RED)
    bar = "█" * int(s / 5) + "░" * (20 - int(s / 5))
    print(f"    {dim:<16} [{bar}] {c}{s}%{RESET}  ({p}/{t})")

df.to_csv("sql_dq_report.csv", index=False)
print(f"\n  Rapport CSV : sql_dq_report.csv")
print(f"\n  Étape suivante : python 03_python_dq_pipeline.py\n")

conn.close()
