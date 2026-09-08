# بوابة الاحتمالات

بوت Telegram عربي يحوّل القرارات إلى ثلاثة مسارات بديلة قابلة للاستكشاف.

> التجربة سردية وتأملية وليست تنبؤًا حقيقيًا أو نصيحة مهنية أو طبية أو مالية.

## ما يعمل الآن

- /start لبدء التجربة
- /help لعرض التعليمات
- استقبال أي قرار أو سؤال باللغة العربية
- توليد ثلاثة مسارات: الجريء، الآمن، والغريب
- أزرار لاختيار مسار ومتابعة القصة
- حفظ الجلسات والاختيارات في SQLite
- استخدام نموذج لغوي اختياريًا عبر OPENAI_API_KEY
- وضع احتياطي يعمل بلا نموذج لغوي للمعاينة والتطوير

## التشغيل محليًا

1. أنشئ بوتًا من @BotFather وخذ TELEGRAM_BOT_TOKEN.
2. انسخ .env.example إلى .env.
3. ضع المفاتيح في بيئة التشغيل، وليس في GitHub.
4. ثبّت الاعتمادات:

       python -m venv .venv
       source .venv/bin/activate
       pip install -r requirements.txt

5. شغّل:

       python -m app.main

## المتغيرات

- TELEGRAM_BOT_TOKEN: مطلوب
- OPENAI_API_KEY: اختياري لتوليد قصص أكثر تخصيصًا
- OPENAI_MODEL: افتراضيًا gpt-4o-mini
- DATABASE_PATH: افتراضيًا data/possibilities.db

## تشغيل Docker

       docker build -t possibilities-bot .
       docker run --env-file .env possibilities-bot

## الخطوة التالية

إضافة جدولة رسائل يومية، صور رمزية للمسارات، ونظام نهايات متعددة لكل قرار.
