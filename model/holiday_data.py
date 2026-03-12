import pandas as pd
import holidays


def get_ethiopian_holidays(start_year=2023, end_year=2030):

    et_holidays = holidays.country_holidays(
        "ET",
        years=range(start_year, end_year + 1)
    )

    holiday_list = []

    for date, name in et_holidays.items():
        holiday_list.append({
            "holiday": name,
            "ds": pd.to_datetime(date),
            "lower_window": -1,
            "upper_window": 2
        })

    holidays_df = pd.DataFrame(holiday_list)

    return holidays_df