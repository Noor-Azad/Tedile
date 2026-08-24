def format_datetime(value):
    """Format stored datetimes for users without changing their timezone."""
    if value is None:
        return ""
    return f"{value.day} {value.strftime('%b %Y, %I:%M %p')}"
