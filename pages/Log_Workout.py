import streamlit as st
from datetime import date
from dao.workout_dao import read_workout_types, log_workout, read_workouts

def app():
    st.title("Log Workout")

    # --- SELECT / LOG WORKOUT ---
    all_types = read_workout_types()
    type_options = [wt["workout_type"] for wt in all_types]

    if not type_options:
        st.warning("No workout types defined. Please create some in 'Create Workout Type' page.")
        return

    workout_type_sel = st.selectbox("Choose workout type", type_options)

    # We need to retrieve info on whether it is int or float
    selected_type_info = next((wt for wt in all_types if wt["workout_type"] == workout_type_sel), None)
    use_int = selected_type_info["is_int"] if selected_type_info else False
    unit = selected_type_info["unit"] if selected_type_info else ""

    workout_date = st.date_input("Date", date.today())

    # If is_int, we only allow integer input; otherwise float
    if use_int:
        amount = st.number_input("Amount (integer)", value=0, step=1)
    else:
        amount = st.number_input("Amount (float)", value=0.0, step=0.1)

    if st.button("Log Workout"):
        log_workout(workout_type_sel, workout_date, float(amount), unit)
        st.success(f"Logged {amount} {unit} for {workout_type_sel} on {workout_date}.")

    st.write("---")

    # --- FILTER AND LIST WORKOUTS ---
    st.subheader("Past Workouts")
    filter_type = st.selectbox("Filter by type (optional)", [""] + type_options)
    filtered_type = filter_type if filter_type else None
    workouts = read_workouts(filtered_type)

    if not workouts:
        st.write("No workouts found.")
    else:
        for w in workouts:
            display_amt = w["amount"]
            # If is_int for that workout type, cast to int for display
            matching_type = next((t for t in all_types if t["workout_type"] == w["workout_type"]), None)
            if matching_type and matching_type["is_int"]:
                display_amt = int(display_amt)

            st.write(f"{w['date']}: {w['workout_type']} - {display_amt} {w['unit']}")
