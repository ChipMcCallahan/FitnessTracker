import streamlit as st
from dao.workout_dao import ensure_dataset_and_tables

def main():
    # Make sure BigQuery dataset & tables exist
    ensure_dataset_and_tables()

    st.title("Fitness Tracker Home")
    st.write("Welcome to the Fitness Tracker App! Use the sidebar to navigate.")

if __name__ == "__main__":
    main()
