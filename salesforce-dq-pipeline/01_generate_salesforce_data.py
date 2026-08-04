"""
PROJET : Salesforce CRM — Data Quality Pipeline
================================================
Simule un export Salesforce des 4 objets CRM principaux :
  - Account       (comptes clients/entreprises)
  - Contact       (contacts rattachés aux comptes)
  - Lead          (prospects entrants)
  - Opportunity   (opportunités commerciales)

Chaque objet contient des anomalies réalistes qu'on retrouve
en production Salesforce : doublons, champs manquants, valeurs
incohérentes, violations de règles métier CRM.

Usage : python 01_generate_salesforce_data.py
"""

import pandas as pd
import numpy as np
import sqlite3
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker("fr_FR")
np.random.seed(42)
random.seed(42)

N_ACCOUNTS      = 300
N_CONTACTS      = 600
N_LEADS         = 400
N_OPPORTUNITIES = 500

TODAY = datetime.today()

def rand_date(start_year=2020, end_year=2024):
    start = datetime(start_year, 1, 1)
    end   = datetime(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))

def fmt(dt):
    return dt.strftime("%Y-%m-%d") if dt else None


# ══════════════════════════════════════════════════════════════════
# 1. ACCOUNT — Comptes (entreprises)
# ══════════════════════════════════════════════════════════════════

account_ids = [f"ACC_{str(i).zfill(6)}" for i in range(1, N_ACCOUNTS + 1)]

accounts = pd.DataFrame({
    "Id":               account_ids,
    "Name":             [fake.company() for _ in range(N_ACCOUNTS)],
    "Industry":         np.random.choice(
                            ["Technology","Finance","Healthcare","Retail","Manufacturing","Education","Other"],
                            N_ACCOUNTS, p=[0.25,0.2,0.15,0.15,0.1,0.08,0.07]),
    "AnnualRevenue":    np.round(np.random.uniform(100_000, 50_000_000, N_ACCOUNTS), 2),
    "NumberOfEmployees":np.random.randint(5, 10000, N_ACCOUNTS),
    "BillingCountry":   np.random.choice(["France","Belgique","Suisse","Luxembourg","Allemagne"], N_ACCOUNTS,
                            p=[0.55,0.2,0.1,0.08,0.07]),
    "Phone":            [fake.phone_number() for _ in range(N_ACCOUNTS)],
    "Website":          [f"https://www.{fake.domain_name()}" for _ in range(N_ACCOUNTS)],
    "OwnerId":          [f"USER_{str(random.randint(1,20)).zfill(3)}" for _ in range(N_ACCOUNTS)],
    "CreatedDate":      [fmt(rand_date(2020, 2023)) for _ in range(N_ACCOUNTS)],
    "LastModifiedDate": [fmt(rand_date(2023, 2024)) for _ in range(N_ACCOUNTS)],
    "Type":             np.random.choice(["Customer","Prospect","Partner","Competitor"], N_ACCOUNTS,
                            p=[0.5,0.3,0.15,0.05]),
    "Rating":           np.random.choice(["Hot","Warm","Cold", None], N_ACCOUNTS, p=[0.3,0.4,0.2,0.1]),
})

# ── Anomalies Accounts ──────────────────────────────────────────
accounts.loc[2,  "Name"]             = None                      # Nom nul
accounts.loc[5,  "Name"]             = ""                        # Nom vide
accounts.loc[10, "AnnualRevenue"]    = -5000                     # Revenu négatif
accounts.loc[15, "AnnualRevenue"]    = None
accounts.loc[20, "NumberOfEmployees"]= 0                         # 0 employé
accounts.loc[25, "NumberOfEmployees"]= -10
accounts.loc[30, "BillingCountry"]   = "XX"                      # Pays inconnu
accounts.loc[35, "Phone"]            = "000"                     # Téléphone invalide
accounts.loc[40, "Website"]          = "pas_un_site"             # URL invalide
accounts.loc[45, "CreatedDate"]      = "2035-01-01"              # Date future
accounts.loc[50, "LastModifiedDate"] = "2019-01-01"              # ModifiedDate < CreatedDate possible
accounts.loc[55, "Industry"]         = "SECTEUR_INCONNU"         # Valeur picklist invalide
accounts.loc[60, "Type"]             = None

# Doublons Account (même nom, Phone différent — doublon typique Salesforce)
dup_acc = accounts.iloc[1].copy()
dup_acc["Id"]    = "ACC_DUP001"
dup_acc["Phone"] = fake.phone_number()
accounts = pd.concat([accounts, pd.DataFrame([dup_acc])], ignore_index=True)


# ══════════════════════════════════════════════════════════════════
# 2. CONTACT — Contacts rattachés aux comptes
# ══════════════════════════════════════════════════════════════════

contact_ids = [f"CON_{str(i).zfill(6)}" for i in range(1, N_CONTACTS + 1)]

contacts = pd.DataFrame({
    "Id":           contact_ids,
    "FirstName":    [fake.first_name() for _ in range(N_CONTACTS)],
    "LastName":     [fake.last_name()  for _ in range(N_CONTACTS)],
    "Email":        [fake.email()      for _ in range(N_CONTACTS)],
    "Phone":        [fake.phone_number() for _ in range(N_CONTACTS)],
    "AccountId":    np.random.choice(account_ids, N_CONTACTS),      # FK → Account
    "Title":        np.random.choice(
                        ["CEO","CTO","CFO","Directeur Commercial","Responsable IT","Manager","Autre"],
                        N_CONTACTS),
    "Department":   np.random.choice(["Ventes","Finance","IT","RH","Marketing","Direction"], N_CONTACTS),
    "Salutation":   np.random.choice(["M.","Mme","Dr.","Prof.", None], N_CONTACTS, p=[0.45,0.4,0.05,0.05,0.05]),
    "MailingCountry": np.random.choice(["France","Belgique","Suisse","Luxembourg"], N_CONTACTS,
                            p=[0.6,0.2,0.12,0.08]),
    "LeadSource":   np.random.choice(["Web","Événement","Référence","Email","Appel Sortant", None],
                            N_CONTACTS, p=[0.3,0.2,0.2,0.15,0.1,0.05]),
    "CreatedDate":  [fmt(rand_date(2020, 2024)) for _ in range(N_CONTACTS)],
    "OwnerId":      [f"USER_{str(random.randint(1,20)).zfill(3)}" for _ in range(N_CONTACTS)],
    "DoNotCall":    np.random.choice([0, 1], N_CONTACTS, p=[0.85, 0.15]),
    "HasOptedOutOfEmail": np.random.choice([0, 1], N_CONTACTS, p=[0.9, 0.1]),
})

# ── Anomalies Contacts ──────────────────────────────────────────
contacts.loc[3,  "LastName"]    = None                           # Nom nul
contacts.loc[7,  "Email"]       = "email_invalide"               # Format email incorrect
contacts.loc[14, "Email"]       = None                           # Email manquant
contacts.loc[21, "Email"]       = contacts.loc[0, "Email"]      # Email dupliqué
contacts.loc[28, "AccountId"]   = "ACC_FANTOME"                  # FK orpheline
contacts.loc[35, "AccountId"]   = None                           # Contact sans compte
contacts.loc[42, "Phone"]       = "00000"                        # Téléphone invalide
contacts.loc[49, "MailingCountry"] = "PAYS_INCONNU"
contacts.loc[56, "FirstName"]   = None
contacts.loc[63, "LeadSource"]  = "SOURCE_INCONNUE"              # Valeur picklist invalide
contacts.loc[70, "CreatedDate"] = "2035-06-01"                   # Date future

# Doublon contact (même email)
dup_con = contacts.iloc[5].copy()
dup_con["Id"] = "CON_DUP001"
contacts = pd.concat([contacts, pd.DataFrame([dup_con])], ignore_index=True)


# ══════════════════════════════════════════════════════════════════
# 3. LEAD — Prospects entrants
# ══════════════════════════════════════════════════════════════════

lead_ids = [f"LEA_{str(i).zfill(6)}" for i in range(1, N_LEADS + 1)]

leads = pd.DataFrame({
    "Id":           lead_ids,
    "FirstName":    [fake.first_name() for _ in range(N_LEADS)],
    "LastName":     [fake.last_name()  for _ in range(N_LEADS)],
    "Company":      [fake.company()    for _ in range(N_LEADS)],
    "Email":        [fake.email()      for _ in range(N_LEADS)],
    "Phone":        [fake.phone_number() for _ in range(N_LEADS)],
    "Status":       np.random.choice(
                        ["Nouveau","Contacté","Qualifié","Non qualifié","Converti"],
                        N_LEADS, p=[0.3,0.25,0.2,0.15,0.1]),
    "LeadSource":   np.random.choice(
                        ["Web","Événement","Référence","Email","Appel Sortant","Social Media"],
                        N_LEADS, p=[0.35,0.2,0.15,0.15,0.1,0.05]),
    "Rating":       np.random.choice(["Hot","Warm","Cold", None], N_LEADS, p=[0.25,0.45,0.2,0.1]),
    "Industry":     np.random.choice(
                        ["Technology","Finance","Healthcare","Retail","Manufacturing","Other"],
                        N_LEADS),
    "AnnualRevenue":np.round(np.random.uniform(0, 20_000_000, N_LEADS), 2),
    "IsConverted":  np.random.choice([0, 1], N_LEADS, p=[0.85, 0.15]),
    "ConvertedDate":[None] * N_LEADS,   # rempli ci-dessous
    "CreatedDate":  [fmt(rand_date(2021, 2024)) for _ in range(N_LEADS)],
    "OwnerId":      [f"USER_{str(random.randint(1,20)).zfill(3)}" for _ in range(N_LEADS)],
    "Country":      np.random.choice(["France","Belgique","Suisse","Luxembourg","Allemagne"], N_LEADS,
                            p=[0.55,0.2,0.1,0.08,0.07]),
})

# ConvertedDate remplie seulement si IsConverted = 1
leads["ConvertedDate"] = leads.apply(
    lambda r: fmt(rand_date(2022, 2024)) if r["IsConverted"] == 1 else None, axis=1
)

# ── Anomalies Leads ──────────────────────────────────────────────
leads.loc[4,  "LastName"]     = None
leads.loc[9,  "Email"]        = None                             # Email manquant
leads.loc[16, "Email"]        = "mauvais@format"                 # Email invalide
leads.loc[23, "Company"]      = None                             # Entreprise manquante
leads.loc[30, "Status"]       = "STATUT_INCONNU"                 # Valeur picklist invalide
leads.loc[37, "AnnualRevenue"]= -1000
leads.loc[44, "Country"]      = "ZZ"
leads.loc[51, "IsConverted"]  = 1
leads.loc[51, "ConvertedDate"]= None                             # Converti sans date → incohérence
leads.loc[58, "IsConverted"]  = 0
leads.loc[58, "ConvertedDate"]= "2023-05-01"                     # Non converti mais avec date → incohérence
leads.loc[65, "CreatedDate"]  = "2030-01-01"

# Doublon Lead (même email que Contact — lead non dédupliqué)
leads.loc[100, "Email"] = contacts.loc[0, "Email"]


# ══════════════════════════════════════════════════════════════════
# 4. OPPORTUNITY — Opportunités commerciales
# ══════════════════════════════════════════════════════════════════

opp_ids = [f"OPP_{str(i).zfill(6)}" for i in range(1, N_OPPORTUNITIES + 1)]

opportunities = pd.DataFrame({
    "Id":           opp_ids,
    "Name":         [f"Opportunité {fake.company()} - {random.randint(2022,2024)}" for _ in range(N_OPPORTUNITIES)],
    "AccountId":    np.random.choice(account_ids, N_OPPORTUNITIES),  # FK → Account
    "StageName":    np.random.choice(
                        ["Prospection","Qualification","Proposition","Négociation","Gagné","Perdu"],
                        N_OPPORTUNITIES, p=[0.2,0.2,0.2,0.15,0.15,0.1]),
    "Amount":       np.round(np.random.uniform(1000, 500_000, N_OPPORTUNITIES), 2),
    "Probability":  np.random.randint(0, 101, N_OPPORTUNITIES),
    "CloseDate":    [fmt(rand_date(2023, 2025)) for _ in range(N_OPPORTUNITIES)],
    "ForecastCategory": np.random.choice(
                        ["Pipeline","BestCase","Commit","Closed","Omitted"],
                        N_OPPORTUNITIES),
    "OwnerId":      [f"USER_{str(random.randint(1,20)).zfill(3)}" for _ in range(N_OPPORTUNITIES)],
    "CreatedDate":  [fmt(rand_date(2022, 2024)) for _ in range(N_OPPORTUNITIES)],
    "Type":         np.random.choice(
                        ["Nouveau Business","Renouvellement","Upsell","Expansion", None],
                        N_OPPORTUNITIES, p=[0.4,0.25,0.15,0.15,0.05]),
    "LeadSource":   np.random.choice(
                        ["Web","Événement","Référence","Email", None],
                        N_OPPORTUNITIES, p=[0.3,0.2,0.2,0.2,0.1]),
    "IsWon":        [0] * N_OPPORTUNITIES,
    "IsClosed":     [0] * N_OPPORTUNITIES,
})

# Cohérence IsWon / IsClosed / StageName
opportunities["IsWon"]    = opportunities["StageName"].eq("Gagné").astype(int)
opportunities["IsClosed"] = opportunities["StageName"].isin(["Gagné","Perdu"]).astype(int)

# ── Anomalies Opportunities ──────────────────────────────────────
opportunities.loc[6,  "Amount"]       = -2500                   # Montant négatif
opportunities.loc[12, "Amount"]       = None                    # Montant nul
opportunities.loc[18, "Amount"]       = 0                       # Montant zéro
opportunities.loc[24, "Probability"]  = 150                     # Probabilité > 100
opportunities.loc[30, "Probability"]  = -10
opportunities.loc[36, "AccountId"]    = "ACC_FANTOME2"          # FK orpheline
opportunities.loc[42, "CloseDate"]    = None                    # Date de clôture manquante
opportunities.loc[48, "StageName"]    = "ÉTAPE_INCONNUE"        # Picklist invalide
opportunities.loc[54, "Name"]         = None
# Incohérence : StageName=Gagné mais IsWon=0
opportunities.loc[60, "StageName"]    = "Gagné"
opportunities.loc[60, "IsWon"]        = 0
# Incohérence : Probability=100 mais StageName=Prospection
opportunities.loc[66, "Probability"]  = 100
opportunities.loc[66, "StageName"]    = "Prospection"
# CloseDate dans le passé mais StageName = Pipeline (opp oubliée)
opportunities.loc[72, "CloseDate"]    = "2022-03-15"
opportunities.loc[72, "StageName"]    = "Pipeline"
opportunities.loc[78, "ForecastCategory"] = "CATÉGORIE_INCONNUE"
opportunities.loc[84, "CreatedDate"]  = "2028-01-01"            # Date future


# ══════════════════════════════════════════════════════════════════
# SAUVEGARDE
# ══════════════════════════════════════════════════════════════════

conn = sqlite3.connect("salesforce_dq.db")
accounts.to_sql("Account",      conn, if_exists="replace", index=False)
contacts.to_sql("Contact",      conn, if_exists="replace", index=False)
leads.to_sql("Lead",            conn, if_exists="replace", index=False)
opportunities.to_sql("Opportunity", conn, if_exists="replace", index=False)
conn.close()

accounts.to_csv("sf_accounts.csv",      index=False)
contacts.to_csv("sf_contacts.csv",      index=False)
leads.to_csv("sf_leads.csv",            index=False)
opportunities.to_csv("sf_opportunities.csv", index=False)

print("=" * 58)
print("  EXPORT SALESFORCE SIMULÉ")
print("=" * 58)
print(f"  Account      : {len(accounts)} lignes")
print(f"  Contact      : {len(contacts)} lignes")
print(f"  Lead         : {len(leads)} lignes")
print(f"  Opportunity  : {len(opportunities)} lignes")
print("=" * 58)
print("  Fichiers créés :")
print("   salesforce_dq.db")
print("   sf_accounts.csv / sf_contacts.csv")
print("   sf_leads.csv / sf_opportunities.csv")
print("\n  Étape suivante : python 02_sql_dq_checks.py")
