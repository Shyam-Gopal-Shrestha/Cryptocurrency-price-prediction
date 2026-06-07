from api.services import market_service, ml_service


def evaluate_alert_condition(alert, latest_price=None, pct_change_24h=None, sentiment_label=None):
    return ml_service.evaluate_alert_condition(alert, latest_price, pct_change_24h, sentiment_label)


def run_alert_email_cycle(*args, **kwargs):
    return market_service.run_alert_email_cycle(*args, **kwargs)
