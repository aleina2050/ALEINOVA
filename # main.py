# main.py
# pip install fastapi uvicorn pydantic

from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict
import math

app = FastAPI(title="Therapeutic Nutrition AI Assistant")

Sex = Literal["male", "female"]
Activity = Literal["sedentary", "light", "moderate", "active", "very_active"]
Goal = Literal["weight_loss", "maintenance", "weight_gain"]
Condition = Literal[
    "healthy", "diabetes", "hypertension", "ckd", "obesity",
    "pregnancy", "lactation", "heart_disease", "ibs"
]

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9
}

class LabResult(BaseModel):
    name: str
    value: float
    unit: str

class FoodItem(BaseModel):
    name: str
    amount: float
    unit: str
    meal: Optional[str] = None
    cooking_method: Optional[str] = None

class PatientInput(BaseModel):
    age: int = Field(..., ge=1, le=120)
    sex: Sex
    weight_kg: float
    height_cm: float
    activity: Activity
    goal: Goal
    conditions: List[Condition] = ["healthy"]
    symptoms: List[str] = []
    labs: List[LabResult] = []
    preferences: List[str] = []
    allergies: List[str] = []
    medications: List[str] = []
    recall_24h: List[FoodItem] = []

def bmi(weight_kg: float, height_cm: float) -> float:
    h = height_cm / 100
    return round(weight_kg / (h * h), 1)

def bmi_category(value: float) -> str:
    if value < 18.5:
        return "نقص وزن"
    if value < 25:
        return "وزن صحي"
    if value < 30:
        return "زيادة وزن"
    return "سمنة"

def mifflin_st_jeor(patient: PatientInput) -> float:
    if patient.sex == "male":
        return 10 * patient.weight_kg + 6.25 * patient.height_cm - 5 * patient.age + 5
    return 10 * patient.weight_kg + 6.25 * patient.height_cm - 5 * patient.age - 161

def calories(patient: PatientInput) -> int:
    tdee = mifflin_st_jeor(patient) * ACTIVITY_FACTORS[patient.activity]

    if patient.goal == "weight_loss":
        tdee -= 400
    elif patient.goal == "weight_gain":
        tdee += 300

    if "pregnancy" in patient.conditions:
        tdee += 300
    if "lactation" in patient.conditions:
        tdee += 450

    return max(1200, round(tdee))

def macro_plan(patient: PatientInput, kcal: int) -> Dict:
    """
    نسب مبدئية قابلة للتعديل سريريًا:
    كربوهيدرات 40-50%
    بروتين 15-25%
    دهون 25-35%
    """
    carb_pct = 0.45
    protein_g_per_kg = 1.0
    fat_pct = 0.30

    if "diabetes" in patient.conditions:
        carb_pct = 0.40
        protein_g_per_kg = 1.0
    if "ckd" in patient.conditions:
        protein_g_per_kg = 0.8 # يجب تعديله حسب eGFR ومرحلة المرض
    if "obesity" in patient.conditions:
        protein_g_per_kg = 1.2
    if "pregnancy" in patient.conditions:
        protein_g_per_kg = 1.1

    protein_g = round(patient.weight_kg * protein_g_per_kg)
    protein_kcal = protein_g * 4

    carb_g = round((kcal * carb_pct) / 4)
    fat_g = round((kcal - protein_kcal - carb_g * 4) / 9)

    return {
        "calories_kcal": kcal,
        "carbohydrates_g": carb_g,
        "protein_g": protein_g,
        "fat_g": fat_g,
        "fiber_g": fiber_goal(patient),
        "water_liters": water_goal(patient),
        "notes": macro_notes(patient)
    }

def fiber_goal(patient: PatientInput) -> int:
    # قاعدة عملية: 14 غ ألياف لكل 1000 kcal تقريبًا
    return round(calories(patient) / 1000 * 14)

def water_goal(patient: PatientInput) -> float:
    # تقدير عام: 30-35 ml/kg/day
    base_liters = patient.weight_kg * 35 / 1000
    if "ckd" in patient.conditions:
        return round(base_liters, 2) # يحتاج تعديل حسب السوائل المسموحة طبيًا
    if patient.activity in ["active", "very_active"]:
        base_liters += 0.5
    return round(base_liters, 2)

def macro_notes(patient: PatientInput) -> List[str]:
    notes = []

    if "diabetes" in patient.conditions:
        notes.append("قسّم الكربوهيدرات على الوجبات، وراقب تأثيرها على سكر الدم.")
    if "hypertension" in patient.conditions:
        notes.append("قلّل الصوديوم، وفضّل الأعشاب والليمون بدل الملح.")
    if "ckd" in patient.conditions:
        notes.append("يجب مراجعة البوتاسيوم، الفوسفور، الصوديوم، البروتين والسوائل حسب eGFR.")
    if "heart_disease" in patient.conditions:
        notes.append("قلّل الدهون المشبعة والمقليات، وفضّل زيت الزيتون، السمك، المكسرات غير المملحة.")
    if "ibs" in patient.conditions:
        notes.append("قيّم محفزات القولون، وقد يحتاج المريض لتجربة Low-FODMAP بإشراف مختص.")

    return notes

def smart_questions(patient: PatientInput) -> List[str]:
    questions = [
        "ما الهدف الأساسي للمريض: خفض وزن، ضبط سكر، ضغط، كوليسترول، أعراض هضمية، أم تحسين عام؟",
        "هل توجد أمراض مشخصة أو أدوية تؤثر على الشهية، السكر، الضغط، الكلى أو السوائل؟",
        "هل يوجد فقدان وزن غير مفسر، قيء مستمر، إسهال شديد، دم بالبراز، أو صعوبة بلع؟"
    ]

    if "diabetes" in patient.conditions:
        questions += [
            "ما آخر HbA1c؟ وهل توجد قراءات سكر صائم وبعد الوجبات؟",
            "هل يستخدم المريض إنسولين أو أدوية قد تسبب هبوط السكر؟",
            "ما أكثر الوجبات التي ترفع السكر حسب القياسات؟"
        ]

    if "ckd" in patient.conditions:
        questions += [
            "ما قيمة eGFR والكرياتينين واليوريا؟",
            "هل توجد قيود سوائل؟ وما قيم البوتاسيوم والفوسفور والصوديوم؟"
        ]

    if "hypertension" in patient.conditions:
        questions += [
            "ما متوسط قراءات الضغط المنزلية؟",
            "كم مرة يتناول المريض المخللات، الأطعمة المصنعة، الشوربات الجاهزة أو الوجبات السريعة؟"
        ]

    return questions

def recall_24h_template() -> Dict:
    return {
        "خطوات أخذ 24h recall": [
            "ابدأ بسؤال مفتوح: أخبرني بكل ما أكلته وشربته أمس من الاستيقاظ إلى النوم.",
            "قسّم اليوم إلى: إفطار، سناك، غداء، سناك، عشاء، قبل النوم.",
            "اسأل عن الكميات: كوب، ملعقة، قطعة، وزن تقريبي، حجم الطبق.",
            "اسأل عن طريقة التحضير: مقلي، مشوي، مسلوق، بالزيت، بالزبدة، صوصات.",
            "اسأل عن الإضافات المنسية: سكر، حليب، عصائر، مكسرات، خبز، صلصات.",
            "اسأل عن المكان والوقت والجوع والشبع: في البيت، مطعم، توتر، نهم، أكل ليلي.",
            "راجع القائمة مرة ثانية للتأكد من عدم نسيان مشروبات أو سناكات."
        ]
    }

def analyze_recall(patient: PatientInput) -> Dict:
    flags = []
    meals = {}

    for item in patient.recall_24h:
        meal = item.meal or "غير محدد"
        meals.setdefault(meal, []).append(item.name)

        if item.cooking_method and "fried" in item.cooking_method.lower():
            flags.append(f"{item.name}: يفضل استبدال القلي بالشوي أو الخَبز أو القلاية الهوائية.")
        if any(word in item.name.lower() for word in ["soda", "cola", "juice", "حلويات", "سكر"]):
            flags.append(f"{item.name}: راقب السكر المضاف والكمية.")

    if len(meals) < 3:
        flags.append("قد يكون توزيع الوجبات غير منتظم؛ يُفضّل تقييم الجوع والأكل الليلي.")

    return {
        "meal_distribution": meals,
        "nutrition_flags": flags
    }

def healthy_cooking_tips(patient: PatientInput) -> List[str]:
    tips = [
        "استخدم الشوي، السلق، الطهي بالبخار، أو القلاية الهوائية بدل القلي العميق.",
        "اجعل نصف الطبق خضارًا غير نشوية، وربع الطبق بروتينًا، وربع الطبق نشويات كاملة.",
        "استخدم زيت الزيتون بكميات محسوبة بدل السمن والزبدة."
    ]

    if "diabetes" in patient.conditions:
        tips.append("اختر كربوهيدرات عالية الألياف مثل الشوفان، البرغل، البقول، والخبز الأسمر بكميات محسوبة.")
    if "hypertension" in patient.conditions:
        tips.append("استخدم الليمون، الخل، الثوم، البهارات والأعشاب بدل الملح والصلصات المالحة.")
    if "ckd" in patient.conditions:
        tips.append("لا تُعطَ نصائح عالية البوتاسيوم أو البروتين دون مراجعة نتائج التحاليل ومرحلة الكلى.")

    return tips

def alternative_meal_plan(patient: PatientInput, kcal: int) -> Dict:
    return {
        "breakfast": [
            "شوفان + لبن/حليب قليل الدسم + فاكهة مناسبة + مكسرات غير مملحة بكمية صغيرة",
            "بيض مسلوق + خبز حبوب كاملة + خضار"
        ],
        "lunch": [
            "صدر دجاج/سمك مشوي + أرز بني أو برغل + سلطة + زيت زيتون محسوب",
            "عدس أو فاصوليا + سلطة + خبز حبوب كاملة بكمية مناسبة"
        ],
        "dinner": [
            "لبنة/زبادي يوناني + خضار + خبز أسمر",
            "تونة بالماء أو جبن قليل الملح + سلطة"
        ],
        "snacks": [
            "فاكهة كاملة بدل العصير",
            "خضار مقطعة + حمص",
            "حفنة صغيرة مكسرات غير مملحة"
        ],
        "adjustment_note": "الخطة تحتاج تعديل حسب التحاليل، الأدوية، الحساسية، الثقافة الغذائية، والميزانية."
    }

@app.post("/assessment")
def nutrition_assessment(patient: PatientInput):
    patient_bmi = bmi(patient.weight_kg, patient.height_cm)
    kcal = calories(patient)

    return {
        "disclaimer": "هذا النظام مساعد للمتخصص ولا يستبدل التشخيص أو الخطة الطبية الفردية.",
        "anthropometrics": {
            "bmi": patient_bmi,
            "bmi_category": bmi_category(patient_bmi)
        },
        "requirements": macro_plan(patient, kcal),
        "smart_questions": smart_questions(patient),
        "recall_24h_method": recall_24h_template(),
        "recall_24h_analysis": analyze_recall(patient),
        "healthy_cooking_tips": healthy_cooking_tips(patient),
        "alternative_meal_plan": alternative_meal_plan(patient, kcal),
        "red_flags": [
            "هبوط سكر متكرر",
            "فقدان وزن غير مفسر",
            "جفاف شديد",
            "قيء أو إسهال مستمر",
            "ألم صدر أو ضيق نفس",
            "اضطراب شديد في البوتاسيوم أو الصوديوم أو وظائف الكلى"
        ]
    }
