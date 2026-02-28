# project_morphis
Project Morphis: NextGEN Digital Health Assistant 🏥
Problem Statement ID: HC006 | Team: Innovators

Project Overview

Morphis is a hybrid AI-powered healthcare ecosystem designed to transition medical screening from "reactive" to "proactive". Traditional health apps provide static, one-time snapshots that fail to capture gradual health deterioration. Morphis solves this by introducing Symptom Drift Intelligence (SDI)—a time-aware monitoring system that tracks health as a continuous, evolving process.




🚀 Core Innovation: Symptom Drift Intelligence (SDI)
The standout feature of Morphis is the Symptom Drift Index, which continuously evaluates symptom history to detect early warning signals.



Time-Decay Weighting: Recent symptoms are weighted higher, while older entries gradually reduce in impact to reflect current status.


Trend Detection: The system identifies worsening patterns in frequency and severity to trigger proactive risk alerts.



Risk Classification: Categorizes patient status from Green (Low Risk) to Red (Immediate Attention).


🛠️ Technology Stack

Backend: Python / Flask.



Frontend: HTML, CSS, JavaScript, and CustomTkinter.



AI/ML: Gemini Flash 2.5 (Symptom Extraction) and RandomForestClassifier (Disease Prediction).



Database: SQLite for long-term relational health history tracking.


📋 Key Features

AI Chatbot: Provides controlled medical guidance and safe remedies using the Gemini API.



Disease Prediction: Uses a trained ML model to estimate the most probable medical conditions with a confidence score.



Medical Vault: A secure digital space for uploading and managing medical reports.


Doctor Dashboard: Bridges the gap to professional care by providing doctors with structured patient history before consultation.


⚠️ Safety & Constraints

Clinical Support: The system is a decision-support tool, not a diagnostic device; it includes clear disclaimers stating it is not a doctor replacement.



Self-Reporting: We mitigate incorrect user reporting through explainable alerts and encouraging regular updates.
