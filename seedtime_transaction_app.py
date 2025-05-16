import pandas as pd
import streamlit as st
from io import BytesIO, StringIO
from datetime import datetime, timedelta

# Company Name
COMPANY_NAME = "SEETIME CAPITAL MANAGEMENT LIMITED"

# Function to get client's interest rate based on deposit amount and base rate
def get_client_rate(amount, base_rate):
    if amount <= 50000:
        margin = 8.0
    elif 51000 <= amount <= 499000:
        margin = 7.0
    elif amount >= 500000:
        margin = 6.5
    else:
        margin = 8.0
    return base_rate - margin

# Function to compute ROI and update dataframe
def compute_roi(transactions, base_rate, tenor_days):
    transactions = transactions.sort_values('Date').reset_index(drop=True)
    transactions['Client Rate (%)'] = 0.0
    transactions['Tenor (Days)'] = 0
    transactions['Interest Accrued'] = 0.0
    transactions['Cumulative ROI'] = 0.0
    transactions['Balance'] = 0.0

    current_balance = 0.0
    cumulative_roi = 0.0
    last_compound_date = transactions.loc[0, 'Date']
    principal_balance = 0.0

    for idx, row in transactions.iterrows():
        if idx == 0:
            tenor = 0
        else:
            tenor = (row['Date'] - last_compound_date).days

        applicable_rate = get_client_rate(current_balance, base_rate) / 100

        interest_accrued = (current_balance * applicable_rate / 365) * tenor
        cumulative_roi += interest_accrued

        # Compound interest after every 30 days
        if tenor >= 30:
            current_balance += interest_accrued
            last_compound_date = row['Date']

        # Apply transaction
        if row['Type'] == 'Deposit':
            current_balance += row['Amount']
            principal_balance += row['Amount']
        elif row['Type'] == 'Withdrawal':
            current_balance -= row['Amount']
            principal_balance -= row['Amount']

        # Update dataframe
        transactions.at[idx, 'Client Rate (%)'] = round(applicable_rate * 100, 2)
        transactions.at[idx, 'Tenor (Days)'] = tenor
        transactions.at[idx, 'Interest Accrued'] = round(interest_accrued, 2)
        transactions.at[idx, 'Cumulative ROI'] = round(cumulative_roi, 2)
        transactions.at[idx, 'Balance'] = round(current_balance, 2)

    # Handle the case where there is time after the last transaction until tenor ends
    last_date = transactions.iloc[-1]['Date']
    end_date = transactions.iloc[0]['Date'] + timedelta(days=tenor_days)
    remaining_days = (end_date - last_date).days

    if remaining_days > 0:
        applicable_rate = get_client_rate(current_balance, base_rate) / 100
        interest_accrued = (current_balance * applicable_rate / 365) * remaining_days
        cumulative_roi += interest_accrued
        current_balance += interest_accrued

        # Append this as a final row for clarity (optional)
        last_row = {
            'Date': end_date,
            'Type': 'Tenor End Interest',
            'Amount': 0.0,
            'Client Rate (%)': round(applicable_rate * 100, 2),
            'Tenor (Days)': remaining_days,
            'Interest Accrued': round(interest_accrued, 2),
            'Cumulative ROI': round(cumulative_roi, 2),
            'Balance': round(current_balance, 2)
        }
        transactions = pd.concat([transactions, pd.DataFrame([last_row])], ignore_index=True)

    return transactions, round(principal_balance, 2), round(cumulative_roi, 2)

# Streamlit UI
st.title("Transaction Statement Generator")
st.subheader(f"{COMPANY_NAME}")

# Client Info
client_name = st.text_input("Enter Client Name")
account_number = st.text_input("Enter Account Number")
base_rate = st.number_input("Enter Current Base Rate (Annual %)", value=20.66, format="%.2f")
tenor_days = st.number_input("Enter Tenor (Days)", min_value=1, value=365)

st.write("---")
st.subheader("Add Transactions")

# Session state for transaction list
if 'transactions' not in st.session_state:
    st.session_state['transactions'] = []

# Add transaction form
with st.form("transaction_form"):
    t_date = st.date_input("Transaction Date", value=datetime.today())
    t_type = st.selectbox("Type", ['Deposit', 'Withdrawal'])
    t_amount = st.number_input("Amount (₦)", min_value=0.0, step=1000.0)
    submitted = st.form_submit_button("Add Transaction")

    if submitted:
        st.session_state.transactions.append({
            'Date': pd.to_datetime(t_date),
            'Type': t_type,
            'Amount': t_amount
        })
        st.success("Transaction added successfully!")

# Display transactions and compute ROI
if st.session_state.transactions:
    df = pd.DataFrame(st.session_state.transactions)
    st.subheader("Transaction Records")
    st.dataframe(df)

    # Compute ROI and balances with tenor
    result_df, principal_balance, cumulative_roi = compute_roi(df, base_rate, tenor_days)
    total_value = principal_balance + cumulative_roi

    st.subheader("Transaction Statement with ROI Details")
    st.dataframe(result_df)

    # Display Principal Balance, ROI and Total Value
    st.success(f"📊 Principal Balance: ₦{principal_balance:,.2f}")
    st.success(f"💹 Cumulative ROI: ₦{cumulative_roi:,.2f}")
    st.success(f"💰 Total Value (Principal + ROI): ₦{total_value:,.2f}")

    # Line Chart - Principal Balance, Cumulative ROI, Total Value over time
    chart_df = result_df.copy()
    chart_df['Total Value'] = chart_df['Balance'] + chart_df['Cumulative ROI']
    chart_df = chart_df.set_index('Date')[['Balance', 'Cumulative ROI', 'Total Value']]
    st.line_chart(chart_df)

    # Prepare CSV export
    csv_buffer = StringIO()
    header = (
        f"{COMPANY_NAME}\n"
        f"Client Name: {client_name}\n"
        f"Account Number: {account_number}\n\n"
        f"Principal Balance: ₦{principal_balance:,.2f}\n"
        f"Cumulative ROI: ₦{cumulative_roi:,.2f}\n"
        f"Total Value: ₦{total_value:,.2f}\n\n"
    )
    csv_buffer.write(header)
    result_df.to_csv(csv_buffer, index=False)

    # Prepare Excel export
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        header_df = pd.DataFrame({
            '': [
                COMPANY_NAME,
                f'Client Name: {client_name}',
                f'Account Number: {account_number}',
                '',
                f'Principal Balance: ₦{principal_balance:,.2f}',
                f'Cumulative ROI: ₦{cumulative_roi:,.2f}',
                f'Total Value: ₦{total_value:,.2f}',
                ''
            ]
        })
        header_df.to_excel(writer, index=False, header=False, startrow=0, sheet_name='Statement')
        result_df.to_excel(writer, index=False, startrow=9, sheet_name='Statement')

    # Download Buttons
    st.download_button(
        label="Download as CSV",
        data=csv_buffer.getvalue(),
        file_name=f"{client_name}_statement.csv",
        mime="text/csv"
    )

    st.download_button(
        label="Download as Excel",
        data=excel_buffer.getvalue(),
        file_name=f"{client_name}_statement.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No transactions added yet. Add transactions above.")
