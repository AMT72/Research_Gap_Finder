# 🔍 Research Gap Finder

نظام ذكاء اصطناعي يكتشف الثغرات البحثية من الأوراق العلمية تلقائياً.

---

## 🗂️ هيكل المشروع

```
research_gap_finder/
├── app.py              ← واجهة Streamlit الرئيسية
├── pdf_reader.py       ← قراءة وتنظيف ملفات PDF
├── analyzer.py         ← التلخيص وكشف الثغرات (Claude API)
├── report.py           ← توليد تقرير PDF
├── requirements.txt    ← المكتبات المطلوبة
├── .env.example        ← مثال على إعداد الـ API Key
└── README.md
```

---

## ⚙️ التثبيت خطوة بخطوة

### 1. تثبيت Python
تأكد أن عندك Python 3.10 أو أحدث:
```bash
python --version
```

### 2. إنشاء بيئة افتراضية (مستحسن)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. تثبيت المكتبات
```bash
pip install -r requirements.txt
```

### 4. إعداد الـ API Key
انسخ ملف `.env.example` وسمّه `.env`:
```bash
cp .env.example .env
```
ثم افتحه وضع مفتاحك:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxx
```

احصل على مفتاحك مجاناً من: https://console.anthropic.com

### 5. تشغيل التطبيق
```bash
streamlit run app.py
```

سيفتح المتصفح تلقائياً على: http://localhost:8501

---

## 🚀 طريقة الاستخدام

1. افتح التطبيق في المتصفح
2. أدخل الـ API Key في الشريط الجانبي
3. ارفع 2-10 ملفات PDF (أوراق بحثية)
4. اضغط **ابدأ التحليل**
5. انتظر دقيقتين تقريباً
6. شاهد النتائج وحمّل التقرير PDF

---

## 📊 ما يقدمه النظام

| الميزة | الوصف |
|--------|--------|
| ملخص كل ورقة | الطريقة، البيانات، النتائج، القيود |
| Comparison Matrix | جدول مقارنة لكل الأوراق |
| Research Gaps | ثغرات بحثية مع Novelty Score من 10 |
| Idea Generator | أفكار بحثية مقترحة مع تقييم الجدوى |
| Citation Graph | شبكة العلاقات بين الأوراق |
| تقرير PDF | تقرير احترافي قابل للتحميل |

---

## 🔑 الحصول على API Key

1. اذهب إلى https://console.anthropic.com
2. أنشئ حساباً مجانياً
3. اذهب إلى API Keys
4. انشئ مفتاحاً جديداً
5. الـ free tier يكفي لتجربة المشروع

---

## ❓ حل المشاكل الشائعة

**المشكلة: `ModuleNotFoundError`**
```bash
pip install -r requirements.txt
```

**المشكلة: `AuthenticationError`**
- تحقق من صحة الـ API Key
- تأكد أنك أدخلته في الشريط الجانبي

**المشكلة: الورقة "قصيرة جداً"**
- الملف قد يكون محمياً أو ممسوحاً ضوئياً (صور فقط)
- جرب ورقة أخرى

**المشكلة: `streamlit: command not found`**
```bash
python -m streamlit run app.py
```

---

## 🛠️ التطوير المستقبلي

- [ ] دعم جلب الأوراق من Arxiv تلقائياً
- [ ] واجهة عربية كاملة
- [ ] تحليل الاستشهادات الفعلية
- [ ] دعم ملفات Word
