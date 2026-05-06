# Crypto Price Prediction

## Hourly Email Alerts

The backend now evaluates enabled user alerts every hour and sends an email through EmailJS when an alert is triggered.

Add these variables to `.env`:

```env
EMAILJS_SERVICE_ID=your_service_id
EMAILJS_TEMPLATE_ID=your_template_id
EMAILJS_PUBLIC_KEY=your_public_key
EMAILJS_PRIVATE_KEY=your_private_key
ALERT_EMAIL_INTERVAL_SECONDS=3600
```

`ALERT_EMAIL_INTERVAL_SECONDS` defaults to `3600` seconds.

Your EmailJS template can use these parameters:

- `to_email`
- `user_email`
- `symbol`
- `alert_type`
- `direction`
- `threshold_value`
- `sentiment_label`
- `latest_price`
- `pct_change_24h`
- `reason`
- `triggered_at`

The alert scheduler runs in the FastAPI backend, so email delivery continues even when the frontend dashboard is closed.
