import requests
import json
import re

GEMINI_API_KEY = "AIzaSyBWKCtfULw-IqrtA6rsy4p0reT603LEp4Y"   # ⚠️ Never hardcode in production
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

OFFICIAL_SYMPTOMS = [
    "abdominal_pain","abnormal_menstruation","acidity","acute_liver_failure",
    "altered_sensorium","anxiety","back_pain","belly_pain","blackheads",
    "bladder_discomfort","blister","blood_in_sputum","bloody_stool",
    "blurred_and_distorted_vision","breathlessness","brittle_nails","bruising",
    "burning_micturition","chest_pain","chills","cold_hands_and_feets","coma",
    "congestion","constipation","continuous_feel_of_urine","continuous_sneezing",
    "cough","cramps","dark_urine","dehydration","depression","diarrhoea",
    "dischromic_patches","distention_of_abdomen","dizziness",
    "drying_and_tingling_lips","enlarged_thyroid","excessive_hunger",
    "extra_marital_contacts","family_history","fast_heart_rate","fatigue",
    "fluid_overload","foul_smell_of_urine","headache","high_fever",
    "hip_joint_pain","history_of_alcohol_consumption","increased_appetite",
    "indigestion","inflammatory_nails","internal_itching","irregular_sugar_level",
    "irritability","irritation_in_anus","itching","joint_pain","knee_pain",
    "lack_of_concentration","lethargy","loss_of_appetite","loss_of_balance",
    "loss_of_smell","malaise","mild_fever","mood_swings","movement_stiffness",
    "mucoid_sputum","muscle_pain","muscle_wasting","muscle_weakness","nausea",
    "neck_pain","nodal_skin_eruptions","obesity","pain_behind_the_eyes",
    "pain_during_bowel_movements","pain_in_anal_region","painful_walking",
    "palpitations","passage_of_gases","patches_in_throat","phlegm","polyuria",
    "prominent_veins_on_calf","puffy_face_and_eyes","pus_filled_pimples",
    "receiving_blood_transfusion","receiving_unsterile_injections",
    "red_sore_around_nose","red_spots_over_body","redness_of_eyes",
    "restlessness","runny_nose","rusty_sputum","scurring","shivering",
    "silver_like_dusting","sinus_pressure","skin_peeling","skin_rash",
    "slurred_speech","small_dents_in_nails","spinning_movements",
    "spotting_urination","stiff_neck","stomach_bleeding","stomach_pain",
    "sunken_eyes","sweating","swelled_lymph_nodes","swelling_joints",
    "swelling_of_stomach","swollen_blood_vessels","swollen_extremeties",
    "swollen_legs","throat_irritation","toxic_look_(typhos)",
    "ulcers_on_tongue","unsteadiness","visual_disturbances","vomiting",
    "watering_from_eyes","weakness_in_limbs","weakness_of_one_body_side",
    "weight_gain","weight_loss","yellow_crust_ooze","yellow_urine",
    "yellowing_of_eyes","yellowish_skin"
]


def extract_symptoms(text):

    prompt = f"""
You are a medical symptom normalization system.

User text:
"{text}"

Map the description to the CLOSEST matching symptom(s)
from the official symptom list below.

IMPORTANT RULES:
- Understand natural language.
- Handle synonyms.
- Infer meaning (example: high temperature → high_fever).
- Only return symptoms that exist in the list.
- Do NOT invent new symptoms.
- If nothing matches, return empty array.

Official symptom list:
{OFFICIAL_SYMPTOMS}

Also detect intensity:
- mild
- severe
- none

Return ONLY JSON:

{{
  "symptoms": [],
  "intensity": "mild/severe/none"
}}
"""

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        response = requests.post(
            f"{API_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=payload,
            timeout=20
        )

        if response.status_code != 200:
            print("Gemini API Error:", response.text)
            return {"symptoms": [], "intensity": "none"}

        result = response.json()

        raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
        print("RAW GEMINI TEXT:", raw_text)

        # Extract JSON safely
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)

        if not json_match:
            return {"symptoms": [], "intensity": "none"}

        parsed = json.loads(json_match.group())

        valid_symptoms = []

        for s in parsed.get("symptoms", []):
            normalized = s.lower().strip().replace(" ", "_")
            if normalized in OFFICIAL_SYMPTOMS:
                valid_symptoms.append(normalized)

        intensity = parsed.get("intensity", "none")

        if intensity not in ["mild", "severe", "none"]:
            intensity = "none"

        return {
            "symptoms": valid_symptoms,
            "intensity": intensity
        }

    except Exception as e:
        print("Parsing/Request error:", e)
        return {"symptoms": [], "intensity": "none"}
    
import requests
import json
import re

def generate_ai_recommendations(symptoms, phase, sdi_score, age, chronic):
    """
    Generate structured AI recommendations based on:
    - Symptoms
    - Phase (low/moderate/high)
    - SDI score (0–100)
    - Age
    - Chronic disease
    """

    # -----------------------------
    # 1️⃣ Convert SDI → Risk Level
    # -----------------------------
    if sdi_score <= 25:
        risk_level = "Low"
    elif sdi_score <= 50:
        risk_level = "Moderate"
    elif sdi_score <= 75:
        risk_level = "High"
    else:
        risk_level = "Critical"

    # -----------------------------
    # 2️⃣ Structured Prompt
    # -----------------------------
    prompt = f"""
You are a clinical decision assistant.

Patient Information:
Symptoms: {symptoms}
Phase: {phase}
SDI Score: 50
Calculated Risk Level: {risk_level}
Age: {age}
Chronic Condition: {chronic}

Risk Classification Rule:
SDI <=25 → Low
26-50 → Moderate
51-75 → High
>75 → Critical

Respond ONLY in valid JSON format:

{{
  "risk_level": "",
  "immediate_actions": [],
  "home_care": [],
  "medications": [],
  "warnings": [],
  "doctor_required": true
}}

Rules:
- If risk is High or Critical → doctor_required must be true
- If patient age > 60 → increase medical caution
- If chronic condition present → increase caution
- Never provide extreme or unsafe dosages
- Do NOT add explanations outside JSON
"""

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        response = requests.post(
            f"{API_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=payload,
            timeout=15
        )

        if response.status_code != 200:
            return {
                "risk_level": risk_level,
                "immediate_actions": [],
                "home_care": [],
                "medications": [],
                "warnings": ["AI service unavailable."],
                "doctor_required": True if risk_level in ["High", "Critical"] else False
            }

        result = response.json()
        raw_text = result["candidates"][0]["content"]["parts"][0]["text"]

        # -----------------------------
        # 3️⃣ Extract JSON Only
        # -----------------------------
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)

        if not match:
            raise ValueError("No JSON found in AI response")

        parsed = json.loads(match.group())

        # -----------------------------
        # 4️⃣ Basic Safety Validation
        # -----------------------------
        required_keys = [
            "risk_level",
            "immediate_actions",
            "home_care",
            "medications",
            "warnings",
            "doctor_required"
        ]

        for key in required_keys:
            if key not in parsed:
                raise ValueError("Missing required JSON keys")

        return parsed

    except Exception as e:
        # -----------------------------
        # 5️⃣ Fallback Safe Output
        # -----------------------------
        return {
            "risk_level": risk_level,
            "immediate_actions": ["Monitor symptoms closely."],
            "home_care": ["Stay hydrated and rest."],
            "medications": [],
            "warnings": ["Unable to fully analyze symptoms. Consult a doctor if symptoms worsen."],
            "doctor_required": True if risk_level in ["High", "Critical"] else False
        }