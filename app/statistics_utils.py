def get_formatted_percentage(x, tot):
    """
    Return a percentage to one decimal place (respecting )
    """
    return f"{float(x) / tot * 100:.1f}" if tot else "0"
