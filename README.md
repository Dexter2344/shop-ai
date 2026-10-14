# Shop-AI

WhatsApp AI bot for small shops — inventory management, sales tracking, and automated customer service via Meta Cloud API + Gemini.

## Status
- [x] Webhook verify
- [x] Receive messages
- [x] Echo replies
- [ ] Gemini integration
- [ ] Photo → inventory count
- [ ] Sale deduction
- [ ] Low stock alerts
- [ ] Customer-facing bot

## Deploy (Render)

1. New → Web Service
2. Connect GitHub repo `shop-ai`
3. Runtime: Python 3
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables (see below)

### Environment Variables
WHATSAPP_VERIFY_TOKEN=dexter-shop-ai-secret-2026
WHATSAPP_ACCESS_TOKEN=<paste_token_in_render_only>
WHATSAPP_PHONE_NUMBER_ID=1376418208868948


## Test
Send "hi" from your verified WhatsApp number to the test number.
Watch Render logs. Expect an echo reply.

## Built by
Dexter (Okeke Chukwudubem)
