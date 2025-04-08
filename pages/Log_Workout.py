# pages/Log_Workout.py

import streamlit as st
from datetime import date
from typing import Optional
import pandas as pd

from dao.workout_dao import (
    read_workout_types,
    log_workout,
    read_workouts,
)

def app():
    st.title("Log Workout (Append-Only)")

    # 1) Load available workout types
    all_types = read_workout_types()
    type_options = [wt["workout_type"] for wt in all_types]

    if not type_options:
        st.warning("No workout types defined. Please create some in 'Create Workout Type' page.")
        return

    # 2) Input fields: Select type, date, amount
    workout_type_sel = st.selectbox("Choose workout type", type_options)
    selected_type_info = next((wt for wt in all_types if wt["workout_type"] == workout_type_sel), None)
    use_int = selected_type_info["is_int"] if selected_type_info else False
    unit = selected_type_info["unit"] if selected_type_info else ""

    workout_date = st.date_input("Date", date.today())
    if use_int:
        amount = st.number_input("Amount (integer)", value=0, step=1)
    else:
        amount = st.number_input("Amount (float)", value=0.0, step=0.1)

    # 3) Log new workout row (append-only)
    if st.button("Log Workout"):
        log_workout(workout_type_sel, workout_date, float(amount), unit)
        st.success(f"Appended {amount} {unit} for {workout_type_sel} on {workout_date}.")

    st.write("---")
    st.subheader("View Aggregated Workouts")

    # 4) (Optional) Filter
    filter_type = st.selectbox("Filter by type (optional)", [""] + type_options)
    filtered_type: Optional[str] = filter_type if filter_type else None

    # 5) Read all ledger rows from BQ, convert to a DataFrame
    raw_workouts = read_workouts()  # This might return a list of dicts or a DataFrame
    df = pd.DataFrame(raw_workouts) if isinstance(raw_workouts, list) else raw_workouts

    # If the table might be empty, handle that case
    if df.empty:
        st.write("No workouts found.")
        return

    # 6) Aggregate by (workout_type, date)
    #    sum amounts for the day
    grouped_df = (
        df.groupby(["workout_type", "date"], as_index=False)["amount"].sum()
        .sort_values("date", ascending=False)
    )

    # 7) Optional: Filter the aggregated DataFrame
    if filtered_type:
        grouped_df = grouped_df[grouped_df["workout_type"] == filtered_type]

    # 8) Display aggregated daily totals
    st.dataframe(grouped_df)

    st.write("Note: We do not update existing rows. Each logging is an append. Daily totals are summed above.")

app()