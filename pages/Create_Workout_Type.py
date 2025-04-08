import streamlit as st
from dao.workout_dao import (
    create_workout_type,
    read_workout_types,
    update_workout_type,
    delete_workout_type
)

def app():
    st.title("Create / Manage Workout Types")

    # --- CREATE NEW TYPE ---
    st.subheader("Create New Workout Type")
    with st.form("create_workout_type"):
        new_type = st.text_input("Workout Type Name")
        new_unit = st.text_input("Unit")
        new_is_int = st.checkbox("Amount is integer (e.g. reps)?")
        submitted = st.form_submit_button("Create Workout Type")
        if submitted:
            if new_type and new_unit:
                create_workout_type(new_type.lower(), new_unit.lower(), new_is_int)
                st.success(f"Workout type '{new_type}' created.")
            else:
                st.warning("Please provide both a workout type name and a unit.")

    st.write("---")

    # --- LIST AND UPDATE / DELETE TYPES ---
    st.subheader("Existing Workout Types")
    workout_types = read_workout_types()

    if workout_types:
        for wt in workout_types:
            with st.expander(f"{wt['workout_type']} - {wt['unit']} (is_int={wt['is_int']})"):
                # UPDATE
                updated_type = st.text_input("New Workout Type Name", wt["workout_type"])
                updated_unit = st.text_input("New Unit", wt["unit"])
                updated_is_int = st.checkbox("Updated is_int?", wt["is_int"])
                if st.button(f"Update {wt['workout_type']}"):
                    update_workout_type(
                        wt["workout_type"],
                        updated_type.lower(),
                        updated_unit.lower(),
                        updated_is_int
                    )
                    st.rerun()

                # DELETE
                if st.button(f"Delete {wt['workout_type']}"):
                    delete_workout_type(wt["workout_type"])
                    st.rerun()
    else:
        st.write("No workout types found.")

app()