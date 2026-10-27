import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime, time

# App Title
st.title("💰 ExpenseMate - Personal Finance Tracker")

# Initialize database
conn = sqlite3.connect("expenses.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        time TEXT,
        category TEXT,
        description TEXT,
        amount REAL
    )
''')
conn.commit()

# Sidebar - Budget Setup
st.sidebar.title("💰 Budget Tracker")
budget = st.sidebar.number_input("Set Monthly Budget (₹)", min_value=0.0, value=10000.0, step=500.0, format="%.2f")

# Sidebar - Navigation
page = st.sidebar.radio("📌 Navigate", ["➕ Add Expense", "❌ Delete Expense", "📊 View Report"])

# Autofill common categories
common_categories = ["Food", "Rent", "Utilities", "Transport", "Entertainment", "Healthcare", "Shopping", "Miscellaneous"]

if page == "➕ Add Expense":
    st.title("➕ Add New Expense")

    with st.form("expense_form"):
        date = st.date_input("📅 Date", datetime.today())
        
        # Time selection in 12-hour format with AM/PM
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_hour = st.selectbox("🕒 Hour", list(range(1, 13)), index=11)
        with col2:
            selected_minute = st.selectbox("⏳ Minute", list(range(0, 60)), index=0)
        with col3:
            selected_am_pm = st.selectbox("☀️ AM/PM", ["AM", "PM"])
        
        if selected_am_pm == "PM" and selected_hour != 12:
            selected_hour += 12
        elif selected_am_pm == "AM" and selected_hour == 12:
            selected_hour = 0
        
        time_selected = time(selected_hour, selected_minute)

        category = st.selectbox("📌 Category", common_categories)
        description = st.text_input("📝 Description")
        amount = st.number_input("💵 Amount (₹)", min_value=0.01, step=0.01, format="%.2f")
        submit = st.form_submit_button("✅ Add Expense")

        if submit:
            cursor.execute("INSERT INTO expenses (date, time, category, description, amount) VALUES (?, ?, ?, ?, ?)",
                           (date.strftime('%Y-%m-%d'), time_selected.strftime('%I:%M %p'), category, description, amount))
            conn.commit()
            st.success("✅ Expense added successfully!")
            st.rerun()

elif page == "❌ Delete Expense":
    st.title("❌ Delete Expense")
    df = pd.read_sql("SELECT * FROM expenses", conn)

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["time"] = pd.to_datetime(df["time"], format='%I:%M %p').dt.strftime('%I:%M %p')
        df_sorted = df.sort_values(by="date", ascending=False)

        df_sorted["display"] = df_sorted["date"].astype(str) + " " + df_sorted["time"] + " - " + df_sorted["category"] + " (₹" + df_sorted["amount"].astype(str) + ")"
        expense_to_delete = st.selectbox("Select an expense to delete", df_sorted["display"])
        delete_button = st.button("🗑️ Delete Selected Expense")

        if delete_button and expense_to_delete:
            selected_row = df_sorted[df_sorted["display"] == expense_to_delete]
            if not selected_row.empty:
                expense_id = int(selected_row["id"].values[0])
                cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
                conn.commit()
                st.success("✅ Expense deleted successfully!")
                st.rerun()
            else:
                st.warning("⚠️ Error finding the selected expense.")
    else:
        st.warning("⚠️ No expenses to delete!")


elif page == "📊 View Report":
    st.title("📊 Monthly Expense Report")

    df = pd.read_sql("SELECT * FROM expenses", conn)

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])

        # Include the current month and months with recorded expenses
        current_month = datetime.today().strftime("%Y-%m")
        available_months = sorted(
            set(df["date"].dt.strftime("%Y-%m").tolist() + [current_month]),
            reverse=True
        )

        selected_month = st.selectbox(
            "📅 Select month",
            available_months,
            format_func=lambda month: datetime.strptime(
                month, "%Y-%m"
            ).strftime("%B %Y")
        )

        # Filter records to the selected month
        monthly_df = df[
            df["date"].dt.strftime("%Y-%m") == selected_month
        ].copy()

        total_spent = monthly_df["amount"].sum()
        remaining_budget = budget - total_spent

        st.subheader("💰 Budget Summary")
        col1, col2 = st.columns(2)

        col1.metric("Total Spent", f"₹{total_spent:,.2f}")
        col2.metric(
            "Remaining Budget",
            f"₹{remaining_budget:,.2f}",
            delta=f"{remaining_budget:,.2f}"
        )

        if remaining_budget < 0:
            st.error(
                f"⚠️ Budget exceeded by ₹{abs(remaining_budget):,.2f}!"
            )
        elif budget > 0 and total_spent >= budget * 0.8:
            st.warning("⚠️ You've used at least 80% of your monthly budget.")
        else:
            st.success("You're within your monthly budget.")

        if not monthly_df.empty:
            monthly_df["time"] = pd.to_datetime(
                monthly_df["time"], format="%I:%M %p"
            ).dt.strftime("%I:%M %p")

            st.subheader("💼 Expenses for Selected Month")
            display_df = monthly_df[
                ["id", "date", "time", "category", "description", "amount"]
            ].copy()
            display_df["date"] = display_df["date"].dt.date
            display_df = display_df.rename(
                columns={"amount": "Amount (₹)"}
            )
            st.dataframe(display_df, use_container_width=True)

            category_expense = (
                monthly_df.groupby("category", as_index=False)["amount"]
                .sum()
            )
            fig = px.pie(
                category_expense,
                names="category",
                values="amount",
                title="Expenses by Category (₹)"
            )
            st.plotly_chart(fig, use_container_width=True)

            daily_expense = (
                monthly_df.groupby("date", as_index=False)["amount"]
                .sum()
                .sort_values("date")
            )
            fig2 = px.line(
                daily_expense,
                x="date",
                y="amount",
                title="Daily Spending (₹)",
                markers=True
            )
            st.plotly_chart(fig2, use_container_width=True)

            csv = monthly_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Monthly Report as CSV",
                csv,
                f"expenses_{selected_month}.csv",
                "text/csv"
            )
        else:
            st.info("No expenses recorded for this month yet.")
    else:
        st.warning("⚠️ No expenses recorded yet!")


# Close database connection
conn.close()
