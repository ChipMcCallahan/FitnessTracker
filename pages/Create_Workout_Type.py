import streamlit as st
from dao.workout_dao import (
    create_workout_type,
    read_workout_types,
    update_workout_type,
    delete_workout_type
)

def app():
    st.title("Create / Manage Workout Types")
    st.info("Note: Effective memory is ~= 1.5 * Half Life")

    # --- CREATE NEW TYPE ---
    st.subheader("Create New Workout Type")
    with st.form("create_workout_type_form"):
        new_type = st.text_input("Workout Type Name")
        new_unit = st.text_input("Unit")
        new_is_int = st.checkbox("Amount is integer?")
        new_daily_target = st.number_input(
            "Daily Target (float)", min_value=0.0, value=5.0, step=0.5
        )
        # Instead of decay factor:
        new_half_life_days = st.number_input(
            "Half Life (days)", min_value=1.0, value=30.0, step=1.0
        )

        submitted = st.form_submit_button("Create Workout Type")
        if submitted:
            if new_type and new_unit:
                create_workout_type(
                    workout_type=new_type.lower(),
                    unit=new_unit.lower(),
                    is_int=new_is_int,
                    daily_target=new_daily_target,
                    half_life_days=new_half_life_days
                )
                st.success(f"Workout type '{new_type}' created.")
            else:
                st.warning("Please provide both a workout type name and unit.")

    st.write("---")

    # --- LIST AND UPDATE / DELETE TYPES ---
    st.subheader("Existing Workout Types")
    workout_types = read_workout_types()

    if workout_types:
        for wt in workout_types:
            with st.expander(
                f"{wt['workout_type']} - {wt['unit']} "
                f"(is_int={wt['is_int']}, daily_target={wt['daily_target']}, half_life_days={wt['half_life_days']})"
            ):
                key = f"is_int_{wt['workout_type']}"
                updated_type = st.text_input("New Workout Type Name", wt["workout_type"])
                updated_unit = st.text_input("New Unit", wt["unit"])
                updated_is_int = st.checkbox("Updated is_int?", wt["is_int"], key=key)
                updated_daily_target = st.number_input(
                    "Updated Daily Target",
                    min_value=0.0,
                    value=wt["daily_target"],
                    step=0.5,
                    key=key + "_1"
                )
                updated_half_life_days = st.number_input(
                    "Updated Half Life (days)",
                    min_value=1.0,
                    value=wt["half_life_days"],
                    step=1.0,
                    key=key + "_2"
                )

                if st.button(f"Update {wt['workout_type']}"):
                    update_workout_type(
                        old_workout_type=wt["workout_type"],
                        new_workout_type=updated_type.lower(),
                        new_unit=updated_unit.lower(),
                        new_is_int=updated_is_int,
                        new_daily_target=updated_daily_target,
                        new_half_life_days=updated_half_life_days
                    )
                    st.rerun()

                if st.button(f"Delete {wt['workout_type']}"):
                    delete_workout_type(wt["workout_type"])
                    st.rerun()
    else:
        st.write("No workout types found.")

app()