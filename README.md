# 🛠️ DyLib Builder Bot — Windows + GitHub Actions

بوت تيليغرام يستقبل مشاريع C/C++/Swift/ObjC ويحولها لـ `.dylib` حقيقي
باستخدام macOS runner مجاني على GitHub Actions! 🍎

---

## 📁 هيكل المشروع

```
dylib_bot_v2/
├── bot.py                        # البوت الرئيسي
├── config.py                     # الإعدادات
├── requirements.txt              # المكتبات
├── allowed_users.json            # يُنشأ تلقائياً
├── .github/
│   └── workflows/
│       └── build_dylib.yml       # GitHub Actions workflow
├── handlers/
│   ├── auth.py                   # نظام الصلاحيات
│   └── compiler.py              # pipeline كامل
└── utils/
    ├── detector.py               # كشف اللغة
    └── github_api.py            # GitHub API
```

---

## 🚀 خطوات الإعداد

### الخطوة 1 — إنشاء GitHub Repo

1. اذهب إلى https://github.com/new
2. أنشئ repo اسمه `dylib-builder` (يجب أن يكون **public** أو لديك GitHub Pro)
3. افعل `git init` وارفع محتوى المجلد `dylib_bot_v2` كاملاً

```bash
cd dylib_bot_v2
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/USERNAME/dylib-builder.git
git push -u origin main
```

---

### الخطوة 2 — إنشاء GitHub Token

1. اذهب إلى: https://github.com/settings/tokens/new
2. اختر **Classic Token**
3. فعّل الصلاحيات التالية:
   - ✅ `repo` (كامل)
   - ✅ `workflow`
4. انسخ الـ token

---

### الخطوة 3 — إنشاء بوت تيليغرام

1. راسل @BotFather على تيليغرام
2. أرسل `/newbot`
3. اختر اسماً واسم مستخدم للبوت
4. انسخ الـ **Token**

---

### الخطوة 4 — معرفة ID التيليغرام تبعك

1. راسل @userinfobot على تيليغرام
2. سيعطيك معرفك الرقمي (مثل: `123456789`)

---

### الخطوة 5 — ضبط الإعدادات

افتح `config.py` وعدّل هذه القيم:

```python
BOT_TOKEN        = "TOKEN_من_BotFather"
OWNER_ID         = 123456789          # معرفك الرقمي
GITHUB_USERNAME  = "اسم_مستخدمك"
GITHUB_REPO      = "dylib-builder"
GITHUB_TOKEN     = "TOKEN_من_GitHub"
```

---

### الخطوة 6 — تشغيل البوت على Windows

```bash
# تثبيت المكتبات
pip install -r requirements.txt

# تشغيل البوت
python bot.py
```

---

## 🎮 أوامر البوت

| الأمر | الوصف | من يستخدمه |
|-------|--------|------------|
| `/start` | رسالة الترحيب | الجميع المصرح لهم |
| `/help` | المساعدة | الجميع المصرح لهم |
| `/status` | معرفة دورك ومعرفك | الجميع المصرح لهم |
| `/adduser <id>` | إضافة مستخدم | المالك فقط |
| `/removeuser <id>` | حذف مستخدم | المالك فقط |
| `/listusers` | قائمة المستخدمين | المالك فقط |

---

## ⚙️ كيف يعمل البوت

```
المستخدم يرسل .zip
       ↓
البوت يفك الضغط ويكشف اللغة
       ↓
يرفع الأرشيف لـ GitHub Repo
       ↓
يشغّل GitHub Actions على macOS runner
       ↓
clang/swiftc يبني .dylib حقيقي لـ iOS ARM64
       ↓
البوت يحمّل الـ .dylib ويرسله للمستخدم
       ↓
نسخة تُرسل للمالك أيضاً
```

---

## 🌐 اللغات المدعومة

| اللغة | الامتدادات | المترجم |
|-------|-----------|---------|
| 🔵 C | `.c` | clang |
| 🟣 C++ | `.cpp`, `.cxx`, `.cc` | clang++ |
| 🟠 Swift | `.swift` | swiftc |
| 🔴 Objective-C | `.m`, `.mm` | clang |

---

## ⚠️ ملاحظات مهمة

- GitHub Actions يوفر **2000 دقيقة مجانية/شهر** — يكفي للكثير
- وقت كل build حوالي **2-4 دقائق**
- الـ `.dylib` يُحذف من GitHub تلقائياً بعد الإرسال
- الحجم الأقصى للملف: **50MB**
