import streamlit as st
import pandas as pd

st.set_page_config(page_title="مساعد التغذية العلاجية", layout="wide")

ACTIVITY_FACTORS = {
    "قليل الحركة": 1.2,
    "نشاط خفيف": 1.375,
    "نشاط متوسط": 1.55,
    "نشط": 1.725,
    "نشط جدًا": 1.9
}

def calculate_bmi(weight, height_cm):
    height_m = height_cm / 100
    return round(weight / (height_m ** 2), 1)

def bmi_category(bmi):
    if bmi < 18.5:
        return "نقص وزن"
    elif bmi < 25:
        return "وزن طبيعي"
    elif bmi < 30:
        return "زيادة وزن"
    else:
        return "سمنة"

def mifflin_st_jeor(sex, weight, height_cm, age):
    if sex == "ذكر":
        return 10 * weight + 6.25 * height_cm - 5 * age + 5
    else:
        return 10 * weight + 6.25 * height_cm - 5 * age - 161

def calculate_calories(sex, weight, height, age, activity, goal, conditions):
    bmr = mifflin_st_jeor(sex, weight, height, age)
    calories = bmr * ACTIVITY_FACTORS[activity]

    if goal == "نزول وزن":
        calories -= 400
    elif goal == "زيادة وزن":
        calories += 300

    if "حمل" in conditions:
        calories += 300
    if "رضاعة" in conditions:
        calories += 450

    return max(1200, round(calories))

def calculate_macros(weight, calories, conditions):
    carb_pct = 0.45
    protein_per_kg = 1.0

    if "سكري" in conditions:
        carb_pct = 0.40
    if "سمنة" in conditions:
        protein_per_kg = 1.2
    if "مرض كلوي" in conditions:
        protein_per_kg = 0.8
    if "حمل" in conditions:
        protein_per_kg = 1.1

    protein_g = round(weight * protein_per_kg)
    carb_g = round((calories * carb_pct) / 4)
    fat_g = round((calories - protein_g * 4 - carb_g * 4) / 9)
    fiber_g = round((calories / 1000) * 14)
    water_l = round((weight * 35) / 1000, 2)

    return {
        "السعرات الحرارية": calories,
        "الكربوهيدرات / غ": carb_g,
        "البروتين / غ": protein_g,
        "الدهون / غ": fat_g,
        "الألياف / غ": fiber_g,
        "الماء / لتر": water_l
    }

def smart_questions(conditions):
    questions = [
        "ما الهدف الأساسي للمريض؟ نزول وزن، ضبط سكر، ضغط، كوليسترول، أو تحسين عام؟",
        "هل توجد أدوية حالية؟",
        "هل يوجد فقدان وزن غير مفسر أو قيء أو إسهال مستمر؟",
        "هل توجد حساسية أو عدم تحمل لبعض الأطعمة؟"
    ]

    if "سكري" in conditions:
        questions += [
            "ما آخر نتيجة HbA1c؟",
            "هل توجد قراءات سكر صائم وبعد الوجبات؟",
            "هل يستخدم المريض إنسولين أو أدوية تسبب هبوط السكر؟"
        ]

    if "ضغط" in conditions:
        questions += [
            "ما متوسط قراءات الضغط؟",
            "كم مرة يتناول المريض المخللات أو الأطعمة المصنعة أو الوجبات السريعة؟"
        ]

    if "مرض كلوي" in conditions:
        questions += [
            "ما قيمة eGFR والكرياتينين؟",
            "ما قيم البوتاسيوم والفوسفور والصوديوم؟",
            "هل توجد قيود على السوائل؟"
        ]

    return questions

def analyze_recall(recall_df):
    notes = []

    if recall_df.empty:
        return ["لم يتم إدخال بيانات 24h recall بعد."]

    meals_count = recall_df["الوجبة"].nunique()

    if meals_count < 3:
        notes.append("توزيع الوجبات قد يكون غير منتظم؛ يفضّل تقييم الجوع والأكل الليلي.")

    for _, row in recall_df.iterrows():
        food = str(row["الصنف"]).lower()
        cooking = str(row["طريقة التحضير"]).lower()

        if "مقلي" in cooking:
            notes.append(f"{row['الصنف']}: يفضّل استبدال القلي بالشوي أو السلق أو القلاية الهوائية.")

        if any(word in food for word in ["cola", "soda", "عصير", "حلويات", "سكر", "بيبسي"]):
            notes.append(f"{row['الصنف']}: انتبه للسكر المضاف والكمية.")

    if not notes:
        notes.append("لا توجد ملاحظات كبيرة من الإدخال الحالي، لكن التحليل يحتاج قاعدة بيانات غذائية لحساب دقيق.")

    return notes

def cooking_tips(conditions):
    tips = [
        "استخدم الشوي، السلق، البخار أو القلاية الهوائية بدل القلي.",
        "اجعل نصف الطبق خضارًا، وربع الطبق بروتينًا، وربع الطبق نشويات كاملة.",
        "استخدم زيت الزيتون بكميات محسوبة بدل السمن والزبدة."
    ]

    if "سكري" in conditions:
        tips.append("اختر كربوهيدرات عالية الألياف مثل الشوفان، البرغل، البقول، والخبز الأسمر بكميات محسوبة.")

    if "ضغط" in conditions:
        tips.append("قلّل الملح والمخللات والمعلبات، واستخدم الليمون والبهارات والأعشاب.")

    if "مرض كلوي" in conditions:
        tips.append("لا ترفع البروتين أو البوتاسيوم دون مراجعة التحاليل ومرحلة مرض الكلى.")

    return tips

def meal_plan(conditions):
    return {
        "الإفطار": [
            "شوفان + لبن قليل الدسم + فاكهة مناسبة",
            "بيض مسلوق + خبز حبوب كاملة + خضار"
        ],
        "الغداء": [
            "دجاج أو سمك مشوي + أرز بني أو برغل + سلطة",
            "عدس أو فاصوليا + سلطة + خبز أسمر بكمية مناسبة"
        ],
        "العشاء": [
            "زبادي يوناني أو لبنة قليلة الدسم + خضار + خبز أسمر",
            "تونة بالماء أو جبن قليل الملح + سلطة"
        ],
        "سناك": [
            "فاكهة كاملة بدل العصير",
            "خضار مقطعة + حمص",
            "مكسرات غير مملحة بكمية صغيرة"
        ]
    }

st.title("🩺 مساعد ذكاء اصطناعي للتغذية العلاجية والحمية")
st.warning("هذا التطبيق مساعد للمتخصص ولا يستبدل التشخيص أو الخطة الطبية الفردية.")

tab1, tab2, tab3 = st.tabs(["بيانات المريض", "24h Recall", "النتائج والخطة"])

with tab1:
    st.header("بيانات المريض")

    col1, col2, col3 = st.columns(3)

    with col1:
        age = st.number_input("العمر", min_value=1, max_value=120, value=30)
        sex = st.selectbox("الجنس", ["ذكر", "أنثى"])
        weight = st.number_input("الوزن / كغ", min_value=20.0, max_value=300.0, value=70.0)

    with col2:
        height = st.number_input("الطول / سم", min_value=80.0, max_value=230.0, value=170.0)
        activity = st.selectbox("مستوى النشاط", list(ACTIVITY_FACTORS.keys()))
        goal = st.selectbox("الهدف", ["نزول وزن", "ثبات وزن", "زيادة وزن"])

    with col3:
        conditions = st.multiselect(
            "الحالة الصحية",
            ["سليم", "سكري", "ضغط", "سمنة", "مرض كلوي", "أمراض قلب", "قولون عصبي", "حمل", "رضاعة"],
            default=["سليم"]
        )
        preferences = st.text_area("تفضيلات المريض الغذائية")
        allergies = st.text_area("الحساسية أو الأطعمة الممنوعة")

with tab2:
    st.header("طريقة أخذ 24h Recall")

    st.markdown("""
    1. اسأل المريض: ماذا أكلت وشربت أمس من وقت الاستيقاظ حتى النوم؟
    2. قسّم اليوم إلى: إفطار، سناك، غداء، سناك، عشاء، قبل النوم.
    3. اسأل عن الكمية: كوب، ملعقة، قطعة، حجم الطبق أو الوزن التقريبي.
    4. اسأل عن طريقة التحضير: مقلي، مشوي، مسلوق، صوصات، زيت، زبدة.
    5. اسأل عن الإضافات المنسية: سكر، حليب، عصائر، صلصات، مكسرات.
    6. راجع اليوم مرة ثانية للتأكد من عدم نسيان أي شيء.
    """)

    st.subheader("إدخال الوجبات")

    recall_data = st.data_editor(
        pd.DataFrame(
            columns=["الوجبة", "الصنف", "الكمية", "الوحدة", "طريقة التحضير"]
        ),
        num_rows="dynamic",
        use_container_width=True
    )

with tab3:
    st.header("النتائج")

    bmi = calculate_bmi(weight, height)
    calories = calculate_calories(sex, weight, height, age, activity, goal, conditions)
    macros = calculate_macros(weight, calories, conditions)

    col1, col2 = st.columns(2)

    with col1:
        st.metric("BMI", bmi)
        st.write("تصنيف BMI:", bmi_category(bmi))

    with col2:
        st.metric("السعرات اليومية المقترحة", calories)

    st.subheader("الاحتياجات اليومية التقريبية")
    st.table(pd.DataFrame(macros.items(), columns=["العنصر", "القيمة"]))

    st.subheader("أسئلة ذكية لتقييم الحالة")
    for q in smart_questions(conditions):
        st.write("•", q)

    st.subheader("تحليل 24h Recall")
    for note in analyze_recall(recall_data):
        st.write("•", note)

    st.subheader("نصائح طهي صحية")
    for tip in cooking_tips(conditions):
        st.write("•", tip)

    st.subheader("اقتراحات بدائل غذائية")
    plan = meal_plan(conditions)
    for meal, options in plan.items():
        st.markdown(f"**{meal}:**")
        for option in options:
            st.write("•", option)

    st.info("للحساب الغذائي الدقيق لكل صنف، اربط التطبيق لاحقًا بقاعدة بيانات مثل USDA FoodData Central أو قاعدة غذائية محلية.")
