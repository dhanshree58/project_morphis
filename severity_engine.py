def adjust_severity(base_severity, user_age, chronic, intensity):

    severity = float(base_severity)

    # Age multiplier
    if user_age > 60:
        severity *= 1.3

    # Chronic condition multiplier
    if chronic:
        severity *= 1.2

    # Intensity multiplier
    if intensity == "severe":
        severity *= 1.4
    elif intensity == "mild":
        severity *= 0.8

    return round(severity, 2)