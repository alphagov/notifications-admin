def get_formatted_percentage(x, tot):
    """
    Return a percentage to one decimal place (respecting )
    """
    return f"{float(x) / tot * 100:.1f}" if tot else "0"


def get_formatted_percentage_two_dp(x, tot):
    """
    Return a percentage to two decimal places
    """
    return f"{float(x) / tot * 100:.2f}" if tot else "0"
