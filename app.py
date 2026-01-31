import os
from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

# ========= Excel =========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = "skincare_services.xlsx"
FILE_PATH = os.path.join(BASE_DIR, EXCEL_FILE)

def norm_list_cell(cell):
    """Comma-separated cell -> list[str] lowercase; remove nan."""
    if pd.isna(cell):
        return []
    items = [x.strip().lower() for x in str(cell).split(",") if x.strip()]
    return [x for x in items if x != "nan"]

def safe_lower(x):
    return str(x).strip().lower() if x is not None else ""

def safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default

def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

# Load Excel once on startup
df = pd.read_excel(FILE_PATH)
df.columns = df.columns.str.strip()  # remove hidden spaces

# Required columns (your Excel)
required_cols = [
    "Service Name", "Skin Type", "Skin Problem", "Min Age", "Max Age",
    "Gender", "Price_PHP", "Base Score", "Notes"
]
for c in required_cols:
    if c not in df.columns:
        if c == "Base Score":
            df["Base Score"] = 0
        else:
            raise ValueError(f"Missing column in Excel: {c}")

# Dropdown data from Excel
gender_options = ["Any", "Male", "Female"]
skin_types_all = sorted({t for cell in df["Skin Type"] for t in norm_list_cell(cell)})
problems_all   = sorted({p for cell in df["Skin Problem"] for p in norm_list_cell(cell)})

# ========= Philippines Provinces + Cities =========
province_options = [
    "Cavite",
    "Abra","Agusan del Norte","Agusan del Sur","Aklan","Albay","Antique","Apayao","Aurora",
    "Basilan","Bataan","Batanes","Batangas","Benguet","Biliran","Bohol","Bukidnon","Bulacan",
    "Cagayan","Camarines Norte","Camarines Sur","Camiguin","Capiz","Catanduanes","Cebu",
    "Cotabato","Davao de Oro","Davao del Norte","Davao del Sur","Davao Occidental","Davao Oriental",
    "Dinagat Islands","Eastern Samar","Guimaras","Ifugao","Ilocos Norte","Ilocos Sur","Iloilo","Isabela",
    "Kalinga","La Union","Laguna","Lanao del Norte","Lanao del Sur","Leyte","Maguindanao del Norte",
    "Maguindanao del Sur","Marinduque","Masbate","Metro Manila","Misamis Occidental","Misamis Oriental",
    "Mountain Province","Negros Occidental","Negros Oriental","Northern Samar","Nueva Ecija","Nueva Vizcaya",
    "Occidental Mindoro","Oriental Mindoro","Palawan","Pampanga","Pangasinan","Quezon","Quirino","Rizal",
    "Romblon","Samar","Sarangani","Siquijor","Sorsogon","South Cotabato","Southern Leyte","Sultan Kudarat",
    "Sulu","Surigao del Norte","Surigao del Sur","Tarlac","Tawi-Tawi","Zambales","Zamboanga del Norte",
    "Zamboanga del Sur","Zamboanga Sibugay"
]

# Cities mapping (ابدأ بـ Cavite كاملة تقريبًا + Metro Manila كأمثلة)
# تقدر تزيد محافظات أخرى بسهولة لاحقًا.
cities_by_province = {
    "Cavite": [
        "Bacoor","Cavite City","Dasmariñas","General Trias","Imus","Tagaytay","Trece Martires",
        "Alfonso","Amadeo","Carmona","General Mariano Alvarez (GMA)","Indang","Kawit",
        "Magallanes","Maragondon","Mendez","Naic","Noveleta","Rosario","Silang","Tanza",
        "Ternate"
    ],
    "Metro Manila": [
        "Caloocan","Las Piñas","Makati","Malabon","Mandaluyong","Manila","Marikina",
        "Muntinlupa","Navotas","Parañaque","Pasay","Pasig","Pateros","Quezon City",
        "San Juan","Taguig","Valenzuela"
    ],
    "Laguna": ["Calamba","Santa Rosa","Biñan","San Pedro","Los Baños","Cabuyao","San Pablo","Sta. Cruz"],
    "Batangas": ["Batangas City","Lipa","Tanauan","Santo Tomas","Nasugbu","Calatagan"],
    "Cebu": ["Cebu City","Mandaue","Lapu-Lapu","Talisay","Toledo"],
}

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    error = None

    # Form defaults
    form_data = {
        "customer_name": "",
        "province": "Cavite",
        "city": "",
        "gender": "Any",
        "age": "",
        "skin_type": "",
        "skin_problems": [],
        "budget": ""
    }

    if request.method == "POST":
        try:
            customer_name = request.form.get("customer_name", "").strip()
            province = request.form.get("province", "Cavite").strip()
            city = request.form.get("city", "").strip()

            gender = safe_lower(request.form.get("gender", "any"))
            age = safe_int(request.form.get("age", 0))
            skin_type = safe_lower(request.form.get("skin_type", ""))
            user_problems = [safe_lower(p) for p in request.form.getlist("skin_problems")]
            budget = safe_float(request.form.get("budget", 0))

            # Keep values after submit
            form_data = {
                "customer_name": customer_name,
                "province": province,
                "city": city,
                "gender": request.form.get("gender", "Any"),
                "age": request.form.get("age", ""),
                "skin_type": request.form.get("skin_type", ""),
                "skin_problems": request.form.getlist("skin_problems"),
                "budget": request.form.get("budget", "")
            }

            scored = []

            for _, row in df.iterrows():
                # Read row values
                row_gender = safe_lower(row.get("Gender", "any"))
                min_age = safe_int(row.get("Min Age", 0))
                max_age = safe_int(row.get("Max Age", 200))
                price = safe_float(row.get("Price_PHP", 0))
                base_score = safe_float(row.get("Base Score", 0))

                # ✅ Budget hard filter (لا نعرض الأغلى من الميزانية)
                if price > budget:
                    continue

                service_skin_types = norm_list_cell(row.get("Skin Type", ""))
                service_problems = norm_list_cell(row.get("Skin Problem", ""))

                score = 0.0

                # Gender (internal only)
                if row_gender in [gender, "any"]:
                    score += 1

                # Age (internal only)
                if min_age <= age <= max_age:
                    score += 1

                # Skin type
                if skin_type and skin_type in service_skin_types:
                    score += 1

                # Problems (any match)
                if user_problems and any(p in service_problems for p in user_problems):
                    score += 1

                # within budget point
                score += 1

                # base score reduced weight
                score += base_score * 0.2

                scored.append({
                    "_score": score,  # internal only
                    "Service Name": str(row.get("Service Name", "")),
                    "Price": price,
                    "Notes": str(row.get("Notes", "")),
                })

            # Sort desc by internal score
            scored.sort(key=lambda x: x["_score"], reverse=True)

            # ✅ Top 5 only
            top5 = scored[:5]

            # remove _score before display
            results = [{"Service Name": r["Service Name"], "Price": r["Price"], "Notes": r["Notes"]} for r in top5]

        except Exception as e:
            error = f"Error: {e}"

    return render_template(
        "index.html",
        gender_options=gender_options,
        skin_types_all=skin_types_all,
        problems_all=problems_all,
        province_options=province_options,
        cities_by_province=cities_by_province,
        results=results,
        form_data=form_data,
        error=error
    )

if __name__ == "__main__":
    app.run(debug=True)
