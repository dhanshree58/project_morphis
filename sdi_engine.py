import sqlite3
import math
from datetime import datetime


import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "health.db")

CRITICAL_SYMPTOMS = [
    "chest_pain",
    "breathlessness",
    "coma",
    "slurred_speech",
    "weakness_of_one_body_side"
]

LAMBDA = 0.25




def age_factor(age):
    if age < 18:
        return 1.0
    elif age < 40:
        return 1.1
    elif age < 60:
        return 1.3
    else:
        return 1.6


def chronic_factor(disease):
    CHRONIC_RISK = {
        "Diabetes": 1.3,
        "Hypertension": 1.4,
        "Heart Disease": 1.8,
        "Asthma": 1.5
    }
    return CHRONIC_RISK.get(disease, 1)




def normalize_score(raw_score):
    k = 0.08
    score = 100 * (1 / (1 + math.exp(-k * raw_score)))
    return round(score, 2)


def risk_color(score):
    if score < 30:
        return "Green"
    elif score < 55:
        return "Yellow"
    elif score < 75:
        return "Orange"
    else:
        return "Red"


def alert_tier(score):
    if score < 30:
        return "Low Risk"
    elif score < 55:
        return "Monitor"
    elif score < 75:
        return "Consult Doctor"
    else:
        return "Immediate Medical Attention"




def detect_trend(current_score, previous_scores, patterns):

    if patterns:
        if "Increasing severity trend" in patterns:
            return "Severity Increasing"
        if "Improving severity trend" in patterns:
            return "Improving"
        if "Symptoms occurring more frequently" in patterns:
            return "Frequency Increasing"

    if previous_scores:
        avg_prev = sum(previous_scores) / len(previous_scores)
        delta = current_score - avg_prev

        if delta > 15:
            return "Rapidly Worsening"
        elif delta > 5:
            return "Increasing"
        elif delta < -10:
            return "Improving"

    return "Stable"




def calculate_sdi(history_rows, age, chronic_disease, previous_scores=None):

    now = datetime.now()

    drift_score = 0
    symptom_frequency = {}
    time_gaps = []
    patterns_detected = []

    previous_date = None
    previous_severity = None
    improvement_count = 0

    if not history_rows:
        return {
            "raw_score": 0,
            "normalized_score": 0,
            "color": "Green",
            "alert": "Low Risk",
            "trend": "No Data",
            "critical": False,
            "patterns": []
        }

    history_rows = sorted(
        history_rows,
        key=lambda x: datetime.fromisoformat(x["date_recorded"])
    )

    for row in history_rows:

        symptom = row["symptom_name"]
        severity = float(row["severity"])
        date_recorded = datetime.fromisoformat(
            row["date_recorded"]
        )

        if symptom in CRITICAL_SYMPTOMS:
            return {
                "raw_score": 120,
                "normalized_score": 100,
                "color": "Red",
                "alert": "Immediate Medical Attention",
                "trend": "Critical",
                "critical": True,
                "patterns": ["Critical symptom detected"]
            }

        days_diff = (now - date_recorded).days + 1
        time_weight = math.exp(-LAMBDA * days_diff)
        drift_score += severity * time_weight

        symptom_frequency[symptom] = symptom_frequency.get(symptom, 0) + 1

        if previous_severity is not None:
            change = severity - previous_severity

            if change > 0:
                if "Increasing severity trend" not in patterns_detected:
                    patterns_detected.append("Increasing severity trend")

            elif change < 0:
                improvement_bonus = abs(change) * 0.5
                drift_score -= improvement_bonus
                improvement_count += 1

                if "Improving severity trend" not in patterns_detected:
                    patterns_detected.append("Improving severity trend")

        if previous_date:
            gap = (date_recorded - previous_date).days
            time_gaps.append(gap)

        previous_date = date_recorded
        previous_severity = severity

    for symptom, count in symptom_frequency.items():
        if count >= 3:
            drift_score += 2
            patterns_detected.append(f"Recurring pattern: {symptom}")

    if len(time_gaps) >= 2:
        if time_gaps[-1] < time_gaps[0]:
            patterns_detected.append("Symptoms occurring more frequently")

    if improvement_count >= 2:
        drift_score *= 0.85

    raw_score = drift_score
    raw_score *= age_factor(age)
    raw_score *= chronic_factor(chronic_disease)

    raw_score = round(max(raw_score, 0), 2)
    normalized = normalize_score(raw_score)
    trend = detect_trend(normalized, previous_scores, patterns_detected)

    return {
        "raw_score": raw_score,
        "normalized_score": normalized,
        "color": risk_color(normalized),
        "alert": alert_tier(normalized),
        "trend": trend,
        "critical": False,
        "patterns": patterns_detected
    }




def get_patient_data(patient_id):

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get age and chronic disease
    cursor.execute(
        "SELECT age, disease FROM Users WHERE user_id=?",
        (patient_id,)
    )
    patient = cursor.fetchone()

    if not patient:
        conn.close()
        return None, None, []

    age = patient["age"]
    chronic = patient["disease"]

    # Fetch actual stored severity
    cursor.execute("""
        SELECT symptom_name, severity, date_recorded
        FROM Health_History
        WHERE user_id=?
    """, (patient_id,))

    history_rows = cursor.fetchall()

    formatted = [
        {
            "symptom_name": row["symptom_name"],
            "severity": row["severity"],
            "date_recorded": row["date_recorded"]
        }
        for row in history_rows
    ]

    conn.close()
    return age, chronic, formatted

def get_previous_scores(user_id):

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT normalized_score
        FROM SDI_History
        WHERE user_id=?
        ORDER BY date_recorded DESC
        LIMIT 5
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return [row["normalized_score"] for row in rows] if rows else None