# pages/Workout_Scores.py
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import timedelta

from dao.workout_dao import read_workout_types, read_workouts

def app():
    st.title("Workout Scores")

    # 1) Read & aggregate logs (append-only data).
    all_workouts = read_workouts()  # Possibly a list of dicts or a DataFrame
    df = pd.DataFrame(all_workouts) if isinstance(all_workouts, list) else all_workouts
    if df.empty:
        st.write("No workout data found.")
        return

    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])

    # Group by (workout_type, date) => daily sum
    grouped = df.groupby(["workout_type", "date"], as_index=False)["amount"].sum()

    # 2) Read workout_types, which includes 'daily_target' and 'half_life_days'
    workout_types = read_workout_types()
    wtypes_df = pd.DataFrame(workout_types)  # [workout_type, unit, is_int, daily_target, half_life_days]

    # --- Pastel color palette for A/B/C/D/F ---
    grade_colors = {
        "A": "#c8f7c5",   # pastel green
        "B": "#f9f7c8",   # pastel yellow
        "C": "#ffe8cc",   # pastel orange
        "D": "#ffd6d6",   # light red
        "F": "#e0e0e0"    # light gray
    }

    def get_grade(score_pct: float) -> str:
        if score_pct >= 90:
            return "A"
        elif score_pct >= 80:
            return "B"
        elif score_pct >= 70:
            return "C"
        elif score_pct >= 60:
            return "D"
        else:
            return "F"

    def apply_extra_credit(A: float, T: float) -> float:
        """
        If daily target = T and actual = A:
          - Everything up to T is full credit
          - Above T is half credit
          => effective = min(A, T) + 0.5 * max(A - T, 0)
        """
        if T <= 0:
            return A  # if T=0, treat all as "normal" or do whatever logic you'd prefer
        base = min(A, T)
        above = max(A - T, 0)
        return base + 0.5 * above

    def ewa_for_type_extra_credit(type_df: pd.DataFrame, half_life_days: float, dtarget: float) -> float:
        """
        Compute an EWA of 'effective amounts' over the last 2*HL days.
        We'll reindex missing days to 0, then transform amounts with extra credit logic,
        then do half-life weighting, summing from earliest_date to last_date.
        """
        if type_df.empty:
            return 0.0

        last_date = type_df["date"].max()
        # limit to 2*HL days
        range_days = int(np.ceil(2.0 * half_life_days))
        earliest_date = last_date - timedelta(days=range_days)

        # filter out older logs
        type_df = type_df[type_df["date"] >= earliest_date].copy()

        # reindex so every day from earliest_date..last_date has a row (with amount=0 if missing)
        all_days = pd.date_range(start=earliest_date, end=last_date, freq="D")
        type_df = type_df.set_index("date")
        type_df = type_df.reindex(all_days, fill_value=0.0)
        type_df = type_df.rename_axis("date").reset_index()  # columns: [date, amount]

        # apply extra credit
        type_df["eff_amount"] = type_df["amount"].apply(lambda x: apply_extra_credit(x, dtarget))

        # half-life weighting
        delta_days = (last_date - type_df["date"]).dt.days
        weights = np.power(2.0, -delta_days / half_life_days)

        weighted_sum = (type_df["eff_amount"] * weights).sum()
        total_weight = weights.sum()
        if total_weight == 0:
            return 0.0
        return weighted_sum / total_weight

    # 3) Build current score table
    score_rows = []
    for _, wt_row in wtypes_df.iterrows():
        wtype = wt_row["workout_type"]
        hl = wt_row["half_life_days"]
        dtarget = wt_row["daily_target"]

        subset = grouped[grouped["workout_type"] == wtype][["date", "amount"]].copy()
        ewa_val = 0.0
        if not subset.empty:
            ewa_val = ewa_for_type_extra_credit(subset, hl, dtarget)

        # final score
        score_pct = (ewa_val / dtarget * 100) if dtarget > 0 else 0.0
        letter = get_grade(score_pct)

        score_rows.append({
            "Workout Type": wtype,
            "EWA": round(ewa_val, 2),
            "Score (%)": round(score_pct, 1),
            "Grade": letter
        })

    scores_df = pd.DataFrame(score_rows)

    st.subheader("Current Scores")

    def highlight_row(row):
        c = grade_colors[row["Grade"]]
        return [f"background-color: {c};" for _ in row]

    if not scores_df.empty:
        df_styled = (
            scores_df.style
            .format({"Score (%)": "{:.1f} %"})  # show 1 decimal plus '%'
            .apply(highlight_row, axis=1)       # color each row by grade
        )
        st.dataframe(df_styled)
    else:
        st.write("No workout types found.")

    st.write("---")
    st.subheader("Score Predictor")

    # intervals + multipliers, now with 0.0, 0.25, etc
    intervals = [0, 1, 3, 7, 14, 30, 45]
    multipliers = [0.0, 0.25, 0.5, 0.6667, 1.0, 1.5, 2.0]

    def compute_future_ewa(subset_df: pd.DataFrame, half_life: float, dtarget: float,
                           daily_amt: float, days_ahead: int) -> float:
        # if no logs yet, assume last_date = today
        if subset_df.empty:
            last_date = pd.Timestamp.today().normalize()
        else:
            last_date = subset_df["date"].max()

        new_data = subset_df.copy()

        new_start_date = last_date + timedelta(days=1)
        new_dates = [new_start_date + timedelta(days=i) for i in range(days_ahead)]
        future_rows = pd.DataFrame({"date": new_dates, "amount": [daily_amt]*days_ahead})
        new_data = pd.concat([new_data, future_rows], ignore_index=True)

        # Then compute EWA with 2*HL day range, but "eff_amount" with extra credit
        return ewa_for_type_extra_credit(new_data, half_life, dtarget)

    for _, wt_row in wtypes_df.iterrows():
        wtype = wt_row["workout_type"]
        hl = wt_row["half_life_days"]
        dtarget = wt_row["daily_target"]

        st.write(f"### {wtype} Predictor")

        # slice
        subset = grouped[grouped["workout_type"] == wtype][["date", "amount"]].copy()

        if subset.empty:
            st.write("No logs yet for this type (using 0 as baseline).")

        pred_data = []
        row_labels = []

        for m in multipliers:
            test_amt = m * dtarget
            row_label = f"{m} x T = {round(test_amt, 2)}"
            row_labels.append(row_label)

            row_scores = []
            for days_ahead in intervals:
                future_val = compute_future_ewa(subset, hl, dtarget, test_amt, days_ahead)
                if dtarget > 0:
                    score_pct = round((future_val / dtarget) * 100, 1)
                else:
                    score_pct = 0.0
                row_scores.append(score_pct)

            pred_data.append(row_scores)

        pred_df = pd.DataFrame(pred_data, columns=intervals, index=row_labels)
        pred_df.index.name = "Daily Amount"

        st.dataframe(pred_df.style.format("{:.1f}"))
        st.write("""
        Above is the projected Score (%) if you do that daily amount for X days, 
        applying our half-life logic and zero baseline for missing data.
        """)

    # ---------------------------------------------------
    # NEW SECTION: Interactive Altair Charts for Each Type
    # ---------------------------------------------------
    st.write("---")
    st.header("Interactive Charts")

    # Let user pick a time range for the chart
    time_options = ["Week", "Month", "Quarter", "Year", "All"]
    time_choice = st.selectbox("Time Range", time_options)
    days_map = {
        "Week": 7,
        "Month": 30,
        "Quarter": 90,
        "Year": 365,
        "All": 9999,
    }
    days_back = days_map[time_choice]

    # We'll define a helper to compute daily EWA for each date in the chart range
    def daily_ewa_scores(subset_df: pd.DataFrame, half_life: float, dtarget: float,
                         future_amt: float = 0.0, future_days: int = 0):
        """
        For each day in the chosen range, compute EWA-based Score.
        Also adds future_amt for 'future_days' after the last real log date.
        Returns DataFrame [date, score, category]
          category can be 'Historical' or 'Future'
        """
        # if no logs => assume last_date= today-1
        if subset_df.empty:
            last_date = pd.Timestamp.today().normalize() - pd.Timedelta(days=1)
        else:
            last_date = subset_df["date"].max()

        # define chart_start based on days_back
        if days_back < 9999:
            chart_start = pd.Timestamp.today().normalize() - pd.Timedelta(days=days_back)
        else:
            # "All" => earliest date or some default
            if not subset_df.empty:
                chart_start = subset_df["date"].min()
            else:
                chart_start = pd.Timestamp.today().normalize() - pd.Timedelta(days=30)

        # define chart_end => we add future_days or 0 if not wanted
        chart_end = pd.Timestamp.today().normalize()
        # we can add a slider if you want to pick how many days in future for the line
        # for now let's just pick future_days
        chart_end_fut = chart_end + pd.Timedelta(days=future_days)

        # Build new_data for future
        new_data = subset_df.copy()
        fut_start_day = last_date + pd.Timedelta(days=1)
        if fut_start_day <= chart_end_fut:
            fut_day_range = pd.date_range(fut_start_day, chart_end_fut, freq="D")
            future_rows = pd.DataFrame({
                "date": fut_day_range,
                "amount": future_amt
            })
            new_data = pd.concat([new_data, future_rows], ignore_index=True)

        # build day range for chart
        all_days = pd.date_range(start=chart_start, end=chart_end_fut, freq="D")

        chart_records = []
        for day in all_days:
            # compute EWA for 'day'
            chart_records.append({
                "date": day,
                "score": ewa_on_day(new_data, day, half_life, dtarget),
            })

        # Mark days <= last_date as 'Historical', beyond that as 'Future'
        df_chart = pd.DataFrame(chart_records)
        df_chart["category"] = np.where(df_chart["date"] <= last_date, "Historical", "Projected")
        return df_chart

    def ewa_on_day(full_df: pd.DataFrame, the_day: pd.Timestamp, half_life: float, target: float) -> float:
        """
        Compute EWA-based Score on 'the_day' using 2*HL back.
        Uses extra-credit transform.
        """
        range_days = int(np.ceil(2.0 * half_life))
        earliest = the_day - pd.Timedelta(days=range_days)

        sub = full_df[(full_df["date"] >= earliest) & (full_df["date"] <= the_day)].copy()
        # reindex
        day_range = pd.date_range(earliest, the_day, freq="D")
        sub = sub.set_index("date").reindex(day_range, fill_value=0.0).rename_axis("date").reset_index()
        sub["eff_amount"] = sub["amount"].apply(lambda x: apply_extra_credit(x, target))

        delta_days = (the_day - sub["date"]).dt.days
        w = np.power(2.0, -delta_days / half_life)
        wsum = (sub["eff_amount"] * w).sum()
        wtot = w.sum()
        if wtot == 0:
            return 0.0
        ewa_val = wsum / wtot
        if target > 0:
            return (ewa_val / target)*100
        return 0.0

    st.write("Select a future daily amount multiplier for the chart projection.")
    chart_mult = st.selectbox("Chart Future Multiplier", [0.0, 0.25, 0.5, 1.0, 1.5, 2.0], index=3)
    future_days_for_chart = st.number_input("Days of future projection in chart", min_value=0, max_value=60, value=30)

    # We'll also define thresholds for A/B/C/D lines
    thr_values = [("A", 90), ("B", 80), ("C", 70), ("D", 60)]

    # Now build a chart for each workout type in wtypes_df
    for _, wt_row in wtypes_df.iterrows():
        wtype = wt_row["workout_type"]
        hl = wt_row["half_life_days"]
        dtarget = wt_row["daily_target"]

        st.write(f"## {wtype} Chart - {time_choice} Range")

        # slice from grouped => daily sums
        sub = grouped[grouped["workout_type"] == wtype][["date","amount"]].copy()
        if sub.empty:
            st.write("No logs => entire chart is 0 until future.")
        sub_chart = daily_ewa_scores(sub, hl, dtarget, future_amt=chart_mult*dtarget, future_days=future_days_for_chart)

        # build threshold df for the same date range
        if not sub_chart.empty:
            chart_start_dt = sub_chart["date"].min()
            chart_end_dt = sub_chart["date"].max()
        else:
            # fallback
            chart_start_dt = pd.Timestamp.today() - pd.Timedelta(days=7)
            chart_end_dt = pd.Timestamp.today()

        threshold_rows = []
        rng = pd.date_range(chart_start_dt, chart_end_dt, freq="D")
        for dt_ in rng:
            for (grade, val) in thr_values:
                threshold_rows.append({
                    "date": dt_,
                    "score": val,  # e.g. 90 for A
                    "category": f"Threshold {grade}"
                })
        thr_df = pd.DataFrame(threshold_rows)

        chart_df = pd.concat([sub_chart, thr_df], ignore_index=True)

        # Build altair chart
        chart = alt.Chart(chart_df).mark_line().encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("score:Q", title="Score (%)", scale=alt.Scale(domain=[0, 110])),
            color=alt.Color(
                "category:N",
                # The domain must match your category labels exactly (case, spelling, etc.)
                scale=alt.Scale(
                    domain=[
                        "Historical",
                        "Projected",
                        "Threshold A",
                        "Threshold B",
                        "Threshold C",
                        "Threshold D",
                    ],
                    range=[
                        "#1f77b4",  # "Historical" => a default blue
                        "#2ca02c",  # "Projected"  => a default green
                        "#c8f7c5",  # "Threshold A" => pastel green
                        "#f9f7c8",  # "Threshold B" => pastel yellow
                        "#ffe8cc",  # "Threshold C" => pastel orange
                        "#ffd6d6",  # "Threshold D" => light red
                    ],
                ),
                legend=alt.Legend(title="Line Type"),  # optional legend title
            ),
            tooltip=["date:T", "score:Q", "category:N"]
        ).properties(
            width=700,
            height=400
        ).interactive()

        st.altair_chart(chart, use_container_width=True)

        st.write(f"**half_life** = {hl}, daily_target={dtarget}, multiplier={chart_mult}, future_days={future_days_for_chart}")
        st.write("Historical vs. Projected lines with threshold lines for A/B/C/D.")


app()