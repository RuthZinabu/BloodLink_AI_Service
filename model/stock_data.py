# model/stock_data.py
def get_current_stock():
    """
    Returns the current stock of all blood types.
    """
    return {
        "O+": 2,
        "A+": 35,
        "B+": 20,
        "AB+": 10,
        "O-": 15,
        "A-": 10,
        "B-": 5,
        "AB-": 2
    }