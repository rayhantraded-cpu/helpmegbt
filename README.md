# المساعد الشخصي والإنجاز

تطبيق عربي شخصي لإدارة المهام والعادات والإنجازات، مبني بـ Flet وPython ومجهز كبنية أولية احترافية للنشر على Android.

## ما الذي تغير في الإصدار 2.0؟

- توحيد التخزين على SQLite بدل الاعتماد الأساسي على JSON.
- استخدام مجلد تخزين التطبيق المناسب على Android عبر `FLET_APP_STORAGE_DATA`.
- دعم إنجاز مستقل لكل فترة: يومية / أسبوعية / شهرية.
- حفظ النقاط والسلسلة والإعدادات داخل قاعدة البيانات.
- استيراد تلقائي محافظ لبيانات `tasks_data.json` القديمة عند أول تشغيل.
- نسخة احتياطية من قاعدة SQLite.
- فصل منطق البيانات عن واجهة Flet.
- إعداد `pyproject.toml` وGitHub Actions لبناء APK وAAB.
- تجهيز معرّف Android ثابت: `com.rayhantrade.personalassistant`.

## التشغيل محليًا

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
flet run src/main.py
```

## بناء Android

```bash
flet build apk
flet build aab
```

Flet يستطيع تجهيز أدوات Android المطلوبة أثناء أول بناء عند الحاجة.

## GitHub

بعد رفع المشروع إلى GitHub على الفرع `main`، سيعمل ملف:

`.github/workflows/android.yml`

على بناء:

- APK للتجربة والتثبيت المباشر.
- AAB كحزمة مناسبة للنشر في Google Play.

### توقيع نسخة النشر

لا تضع ملف keystore أو كلمات المرور داخل GitHub repository.

للنشر الفعلي على Google Play، أنشئ keystore خاصًا بك وخزّن بياناته في GitHub Secrets، ثم اربطها بمتغيرات Flet الخاصة بالتوقيع مثل:

- `FLET_ANDROID_SIGNING_KEY_STORE`
- `FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD`
- `FLET_ANDROID_SIGNING_KEY_PASSWORD`

## هيكل المشروع

```text
personal_assistant_android/
├── .github/
│   └── workflows/
│       └── android.yml
├── src/
│   ├── assets/
│   │   └── icon.png
│   ├── database.py
│   ├── db_operations.py
│   └── main.py
├── .gitignore
├── README.md
├── pyproject.toml
└── requirements.txt
```

## ملاحظات قبل النشر التجاري

هذا الإصدار مناسب كبنية Release Candidate أولية، لكنه ليس بديلًا عن اختبارات النشر النهائية. قبل Google Play نحتاج عادةً إلى:

1. اختبار APK على عدة إصدارات Android وأحجام شاشات.
2. إنشاء أيقونة وهوية بصرية نهائية.
3. إضافة سياسة خصوصية وصفحة دعم.
4. إضافة Crash reporting وAnalytics عند الحاجة وبما يوافق الخصوصية.
5. توقيع AAB بمفتاح إنتاج محفوظ بأمان.
6. مراجعة النصوص، الصلاحيات، وسياسة البيانات.
7. اختبار الترقية من الإصدارات السابقة دون فقدان البيانات.
