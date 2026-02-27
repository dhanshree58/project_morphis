import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import pickle
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(BASE_DIR, "disease_dataset.csv")

df = pd.read_csv(csv_path)
#  Load dataset

print(" Dataset loaded successfully!")
print(df.head())

# Handle missing values 
df.fillna('none', inplace=True)

# Clean and collect unique symptoms
all_symptoms = set()

for col in df.columns[1:]:  # skip 'Disease'
    df[col] = df[col].astype(str).str.strip()    
    all_symptoms.update(df[col].unique())

# remove blanks/none
all_symptoms.discard('none')
all_symptoms.discard('')

#  Create binary columns for each symptom (vectorized way)
print(f"Found {len(all_symptoms)} unique symptoms")

# Efficient one-hot encoding - create all symptom columns at once
symptom_list_sorted = sorted(all_symptoms)
symptom_columns = df.iloc[:, 1:].values  # Get symptom data as numpy array

# Build all symptom columns efficiently
new_columns_dict = {}
for i, symptom in enumerate(symptom_list_sorted):
    if i % 20 == 0:
        print(f"  Processing symptom {i+1}/{len(symptom_list_sorted)}: {symptom}")
    new_columns_dict[symptom] = (symptom_columns == symptom).any(axis=1).astype(int)

# Create new DataFrame from columns and concatenate
new_df = pd.DataFrame(new_columns_dict)
df = pd.concat([df, new_df], axis=1)

#  Prepare X and y
X = df[symptom_list_sorted]
y = df["Disease"]

#  Train/Test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Accuracy
accuracy = accuracy_score(y_test, model.predict(X_test))
print(f" Model trained successfully with accuracy: {accuracy*100:.2f}%")

# Save model + symptom list
with open("disease_model.pkl", "wb") as f:
    pickle.dump(model, f)

pd.DataFrame({"Symptom": symptom_list_sorted}).to_csv("symptom_list.csv", index=False)

print(" Model saved as 'disease_model.pkl'")
print(" Symptom list saved as 'symptom_list.csv'")

#  Test sample (use correct feature order)
sample_input = {symptom: 0 for symptom in symptom_list_sorted}
sample_input["itching"] = 1
sample_input["skin_rash"] = 1

sample_df = pd.DataFrame([sample_input])[symptom_list_sorted]
prediction = model.predict(sample_df)
print(" Predicted Disease:", prediction[0])

