from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

FILE_PATH = "skincare_services.xlsx"

def norm_list_cell(cell):
    """
    Convert a comma-separated cell into a normalized list of lowercase strings.
    """
    if pd.isna(cell):
        return []
    return [x.strip().lower() for x in str(cell).split(",") if x.strip()]

def safe_lower(x):
    return str(x).strip().lower() if not pd.isna(x) else ""

def safe_float(x, default=0.0):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default

def safe_int(x, default=0):
    try:
        if pd.isna(x):
            return default
        return int(x)
    except Exception:
        return default

# ---------- Load Excel ----------
df = pd.read_excel(FILE_PATH)

# Ensure required columns exist (basic safety)
required_cols = [
    "Service Name", "Skin Type", "Skin Problem", "Min Age", "Max Age",
    "Gender", "Price (PHP)", "Base Score", "Notes"
]
for c in required_cols:
    if c not in df.columns:
        # If "Base Score" not found, create it with 0
        if c == "Base Score":
            df["Base Score"] = 0
        else:
            raise ValueError(f"Missing column in Excel: {c}")

# Build dropdown options from Excel
gender_options = ["Any", "Male", "Female"]

skin_types_all = sorted(
    {t for cell in df["Skin Type"] for t in norm_list_cell(cell)}
)
problems_all = sorted(
    {p for cell in df["Skin Problem"] for p in norm_list_cell(cell)}
)

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    form_data = {
        "gender": "Any",
        "age": "",
        "skin_type": "",
        "skin_problems": [],
        "budget": ""
    }
    error = None

    if request.method == "POST":
        try:
            # Read inputs
            gender = safe_lower(request.form.get("gender", "any"))
            age = safe_int(request.form.get("age", 0))
            skin_type = safe_lower(request.form.get("skin_type", ""))
            user_problems = [safe_lower(p) for p in request.form.getlist("skin_problems")]
            budget = safe_float(request.form.get("budget", 0))

            # Keep values to re-fill the form after submit
            form_data = {
                "gender": request.form.get("gender", "Any"),
                "age": request.form.get("age", ""),
                "skin_type": request.form.get("skin_type", ""),
                "skin_problems": request.form.getlist("skin_problems"),
                "budget": request.form.get("budget", "")
            }

            # Scoring / filtering
            for _, row in df.iterrows():
                score = 0.0

                row_gender = safe_lower(row.get("Gender", "any"))
                min_age = safe_int(row.get("Min Age", 0))
                max_age = safe_int(row.get("Max Age", 200))
                price = safe_float(row.get("Price (PHP)", 0))
                base_score = safe_float(row.get("Base Score", 0))

                service_skin_types = norm_list_cell(row.get("Skin Type", ""))
                service_problems = norm_list_cell(row.get("Skin Problem", ""))

                # Gender
                if row_gender in [gender, "any"]:
                    score += 1

                # Age
                if min_age <= age <= max_age:
                    score += 1

                # Skin type
                if skin_type and skin_type in service_skin_types:
                    score += 1

                # Problems (count 1 if any match)
                if user_problems and any(p in service_problems for p in user_problems):
                    score += 1

                # Budget
                if price <= budget:
                    score += 1

                # Base score add-on
                score += base_score

                # Optional: only show services that match at least something meaningful:
                # (example) require budget + age match OR score threshold
                if score > 0:
                    results.append({
                        "Service Name": str(row.get("Service Name", "")),
                        "Score": round(score, 2),
                        "Price": price,
                        "Gender": str(row.get("Gender", "")),
                        "Age Range": f"{min_age}-{max_age}",
                        "Skin Type": str(row.get("Skin Type", "")),
                        "Skin Problem": str(row.get("Skin Problem", "")),
                        "Notes": str(row.get("Notes", "")),
                    })

            # Sort best first
            results.sort(key=lambda x: x["Score"], reverse=True)

        except Exception as e:
            error = f"Error: {e}"

    return render_template(
        "index.html",
        gender_options=gender_options,
        skin_types_all=skin_types_all,
        problems_all=problems_all,
        results=results,
        form_data=form_data,
        error=error
    )

if __name__ == "__main__":
    app.run(debug=True)
