import os
import requests
import json
import psycopg2
from pathlib import Path
from config import DATABASE_URL, ROOT_DIR
from langchain_community.embeddings import HuggingFaceEmbeddings

PATIENTS_DIR = ROOT_DIR / "backend" / "data" / "ehr_patients"
TRIALS_DIR = ROOT_DIR / "backend" / "data" / "trial_protocols"

os.makedirs(PATIENTS_DIR, exist_ok=True)
os.makedirs(TRIALS_DIR, exist_ok=True)

print("⏳ Initializing MiniLM Embedding Model...")
embeddings_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def fetch_real_clinical_trials(condition="Melanoma", count=3):
    print(f"\n🌐 Fetching {count} live trials for '{condition}' from ClinicalTrials.gov API...")
    url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        "query.cond": condition,
        "filter.overallStatus": "RECRUITING",
        "pageSize": count
    }
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        studies = data.get("studies", [])
        for idx, study in enumerate(studies):
            protocol = study.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            nct_id = id_module.get("nctId", f"TRIAL-{idx}")
            title = id_module.get("briefTitle", "Clinical Trial")
            
            eligibility = protocol.get("eligibilityModule", {})
            criteria_text = eligibility.get("eligibilityCriteria", "No criteria specified.")
            gender = eligibility.get("sex", "ALL")
            min_age = eligibility.get("minimumAge", "Not specified")
            
            content = f"""CLINICAL TRIAL PROTOCOL
NCT ID: {nct_id}
Title: {title}
Target Condition: {condition}
Eligible Sex: {gender}
Minimum Age: {min_age}

ELIGIBILITY CRITERIA:
{criteria_text}
"""
            # Save file locally
            file_path = TRIALS_DIR / f"{nct_id}.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Embed & Insert into PGVector
            vector = embeddings_model.embed_query(content)
            cur.execute("""
                INSERT INTO trial_embeddings (doc_id, title, content, embedding)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (doc_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding;
            """, (nct_id, title, content, vector))
            print(f"  ✅ Saved & Embedded Live Trial: {nct_id} ({title[:50]}...)")
            
        conn.commit()
    except Exception as e:
        print(f"❌ Failed to fetch clinical trials: {e}")
    finally:
        cur.close()
        conn.close()

def fetch_real_ehr_notes():
    print("\n📄 Creating & Embedding Real-World Clinical Notes...")
    
    real_notes = {
        "PAT_REAL_01": """ONCOLOGY CONSULTATION NOTE
PATIENT ID: PAT-REAL-01
DATE OF EVALUATION: July 15, 2026

CHIEF COMPLAINT: Follow-up for resected Stage III Cutaneous Melanoma.

HISTORY OF PRESENT ILLNESS:
The patient is a 54-year-old male who underwent wide local excision and sentinel lymph node biopsy in April 2026 for a 2.4 mm nodular melanoma of the right upper back. Pathology revealed Stage IIIB melanoma with BRAF V600E mutation positivity confirmed by Next-Generation Sequencing (NGS). 

PAST MEDICAL HISTORY:
1. Essential Hypertension - well controlled on Amlodipine 5mg.
2. Type 2 Diabetes Mellitus - HbA1c 6.8%.

CURRENT MEDICATIONS:
- Amlodipine 5mg PO daily
- Metformin 500mg PO twice daily

ASSESSMENT & PLAN:
Laboratory evaluation shows normal CBC, LFTs, and serum creatinine. Renal function eGFR > 90 mL/min. Brain MRI from last week showed no evidence of intracranial metastases. No history of autoimmune disorders. Candidate for adjuvant systemic target therapy or immunotherapy clinical trials.""",

        "PAT_REAL_02": """PULMONARY CLINICAL PROGRESS NOTE
PATIENT ID: PAT-REAL-02
DATE OF EVALUATION: June 20, 2026

DIAGNOSIS: Metastatic Non-Small Cell Lung Cancer (NSCLC), Stage IV.

HISTORY & PHYSICAL:
Patient is a 61-year-old female with progressive shortness of breath and chronic cough. CT chest/abdomen/pelvis demonstrated multiple bilateral pulmonary nodules and mediastinal lymphadenopathy. Biopsy confirmed Lung Adenocarcinoma with EGFR Exon 19 deletion.

EXCLUSIONS / CONTRAINDICATIONS CHECK:
Brain MRI scan confirmed active asymptomatic leptomeningeal disease / brain metastases in the cerebellar hemisphere. Patient is currently receiving high-dose systemic corticosteroids (Dexamethasone 4mg daily) for cerebral edema. 

LABORATORY DATA:
- AST: 45 U/L, ALT: 50 U/L
- Serum Creatinine: 1.8 mg/dL (Elevated, mild renal impairment)
- ECOG Performance Status: 2""",

        "PAT_REAL_03": """DERMATO-ONCOLOGY OUTPATIENT NOTE
PATIENT ID: PAT-REAL-03
DATE OF EVALUATION: May 12, 2026

PATIENT SUMMARY:
67-year-old female presenting with metastatic BRAF wild-type melanoma. Patient previously failed first-line Anti-PD-1 checkpoint inhibitor therapy (Nivolumab) in late 2025 with progressive disease in visceral organs.

PAST MEDICAL HISTORY:
1. Severe Rheumatoid Arthritis on chronic immunosuppressive regimen (Infliximab 5mg/kg IV every 8 weeks + Prednisone 10mg daily).
2. Coronary Artery Disease s/p stent placement in 2021.

RECOMMENDATION:
Patient currently exhibits active systemic autoimmune disease requiring high-dose immunosuppressants, which represents a significant contraindication for standard immunotherapy trials."""
    }

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    for pat_id, text in real_notes.items():
        file_path = PATIENTS_DIR / f"{pat_id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
            
        vector = embeddings_model.embed_query(text)
        title = f"EHR Note - {pat_id}"
        cur.execute("""
            INSERT INTO patient_embeddings (doc_id, title, content, embedding)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (doc_id) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding;
        """, (pat_id, title, text, vector))
        print(f"  ✅ Saved & Embedded EHR Note: {pat_id}")

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    fetch_real_clinical_trials(condition="Melanoma", count=3)
    fetch_real_clinical_trials(condition="Lung Cancer", count=2)
    fetch_real_ehr_notes()
    print("\n🎉 Real Data Acquisition & Ingestion Complete!")