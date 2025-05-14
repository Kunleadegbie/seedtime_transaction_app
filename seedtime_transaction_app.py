# Latest script
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

# Company info
COMPANY_NAME = "SEETIME CAPITAL MANAGEMENT LIMITED"
BASE_RATE = 20.66  # p.a.

# Function to get client rate based on deposit amount
def get_client_rate(amount):
    if amount <= 50000:
        return BASE_RATE - 8.66
    elif amount <= 499000:
        return BASE_RATE - 7.66
    else:
        return BASE_RATE - 6.66

# Compounding interest calculator
def compute_compound_interest(principal, rate, days):
    daily_rate = rate / 100 / 365
    return principal * ((1 + daily_rate) ** days - 1)

# Initialize session state for transaction history
if 'transactions' not in st.session_state:
    st.session_state.transactions = []

st.title(f"{COMPANY_NAME} - Client Transaction Statement")

# Input fields
client_name = st.text_input("Client Name")
account_number = st.text_input("Account Number")
tenor = st.number_input("Tenor (days)", min_value=1, step=1)
initial_deposit = st.number_input("Initial Deposit Amount (NGN)", min_value=0.0, step=1000.0)
initial_date = st.date_input("Initial Deposit Date", datetime.today())

additional_deposit = st.number_input("Additional Deposit (optional)", min_value=0.0, step=1000.0)
additional_date = st.date_input("Additional Deposit Date", datetime.today())

withdrawal = st.number_input("Withdrawal (optional)", min_value=0.0, step=1000.0)
withdrawal_date = st.date_input("Withdrawal Date", datetime.today())

if st.button("Add Transaction"):
    if not client_name or not account_number or initial_deposit == 0 or tenor == 0:
        st.error("Please fill all required fields: Client Name, Account Number, Initial Deposit, and Tenor.")
    else:
        # Record initial deposit
        st.session_state.transactions.append({
            "Date": initial_date,
            "Transaction": "Deposit",
            "Amount": initial_deposit
        })
        # Record additional deposit
        if additional_deposit > 0:
            st.session_state.transactions.append({
                "Date": additional_date,
                "Transaction": "Deposit",
                "Amount": additional_deposit
            })
        # Record withdrawal
        if withdrawal > 0:
            st.session_state.transactions.append({
                "Date": withdrawal_date,
                "Transaction": "Withdrawal",
                "Amount": withdrawal
            })
        st.success("Transaction(s) added successfully.")

if st.session_state.transactions:
    df = pd.DataFrame(st.session_state.transactions)
    df.sort_values(by="Date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Compute balances and ROI
    maturity_date = initial_date + pd.to_timedelta(tenor, unit='D')
    deposit_ledger = []
    rows = []

    for i, row in df.iterrows():
        txn_date = row["Date"]
        txn_type = row["Transaction"]
        amount = row["Amount"]

        # Accrue interest on existing deposits up to txn date
        for deposit in deposit_ledger:
            days = (txn_date - deposit['last_updated']).days
            if days > 0:
                rate = get_client_rate(deposit['amount'])
                interest = compute_compound_interest(deposit['amount'], rate, days)
                deposit['roi'] += interest
                deposit['amount'] += interest
                deposit['last_updated'] = txn_date

        # Apply current transaction
        if txn_type == "Deposit":
            deposit_ledger.append({
                "amount": amount,
                "date": txn_date,
                "last_updated": txn_date,
                "roi": 0.0
            })
        elif txn_type == "Withdrawal":
            # Deduct from deposits starting from oldest
            remaining = amount
            deposit_ledger.sort(key=lambda x: x['date'])
            for deposit in deposit_ledger:
                if remaining <= 0:
                    break
                if deposit['amount'] <= remaining:
                    remaining -= deposit['amount']
                    deposit['amount'] = 0
                else:
                    deposit['amount'] -= remaining
                    remaining = 0
            deposit_ledger = [d for d in deposit_ledger if d['amount'] > 0]

        # Calculate total principal and ROI so far
        total_principal = sum(d['amount'] for d in deposit_ledger)
        total_roi = sum(d['roi'] for d in deposit_ledger)

        # Add to rows
        rows.append({
            "Date": txn_date,
            "Transaction": txn_type,
            "Amount": amount,
            "Balance After Txn": round(total_principal, 2),
            "Client Rate (%)": round(get_client_rate(total_principal), 2),
            "Total ROI (NGN)": round(total_roi, 2)
        })

    # At maturity date, compute ROI for remaining days on each deposit
    for deposit in deposit_ledger:
        if deposit['last_updated'] < maturity_date:
            days = (maturity_date - deposit['last_updated']).days
            if days > 0:
                rate = get_client_rate(deposit['amount'])
                interest = compute_compound_interest(deposit['amount'], rate, days)
                deposit['roi'] += interest
                deposit['amount'] += interest
                deposit['last_updated'] = maturity_date

    total_principal = sum(d['amount'] for d in deposit_ledger)
    total_roi = sum(d['roi'] for d in deposit_ledger)
    total_value = total_principal

    # Append final maturity row
    rows.append({
        "Date": maturity_date,
        "Transaction": "Maturity",
        "Amount": 0.0,
        "Balance After Txn": round(total_principal, 2),
        "Client Rate (%)": round(get_client_rate(total_principal), 2),
        "Total ROI (NGN)": round(total_roi, 2)
    })

    final_df = pd.DataFrame(rows)

    st.subheader(f"Transaction Statement for {client_name} ({account_number})")
    st.write(final_df)

    st.write(f"**Maturity Date:** {maturity_date.strftime('%Y-%m-%d')}")
    st.write(f"**Total Net Principal Balance:** NGN {total_principal:,.2f}")
    st.write(f"**Total ROI:** NGN {total_roi:,.2f}")
    st.write(f"**Total Value at Maturity (Principal + ROI):** NGN {total_value:,.2f}")

    # Export to CSV
    csv_data = final_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download CSV",
        data=csv_data,
        file_name=f"{client_name}_{account_number}_statement.csv",
        mime="text/csv"
    )

    # Export to Excel
    def export_excel(dataframe, client_name, account_number):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            dataframe.to_excel(writer, index=False, sheet_name="Statement")
        processed_data = output.getvalue()
        return processed_data

    excel_data = export_excel(final_df, client_name, account_number)

    st.download_button(
        label="Download Excel",
        data=excel_data,
        file_name=f"{client_name}_{account_number}_statement.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
