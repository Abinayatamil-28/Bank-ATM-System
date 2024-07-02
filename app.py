from flask import Flask, render_template, request, Response,redirect, jsonify
import psycopg2
import csv
from io import StringIO
from fpdf import FPDF
from datetime import datetime, timedelta
import hashlib  # For password hashing
import traceback
import decimal  # Import the decimal module

app = Flask(__name__)

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname="bank",
    user="postgres",
    password="1234",
    host="localhost",
    port="5432"
)

conn.autocommit = True
cur = conn.cursor()


# Function to handle the home page
@app.route("/", methods=["GET", "POST"])
def home():
    return render_template("BANKHOME.html")


# Function to handle the signup page
from flask import jsonify

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        account_number = request.form.get('account_number')

        # Hash password before storing
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        existing_user = cur.fetchone()

        if existing_user:
            return jsonify({"message": "User already exists"}), 400  # Return JSON response for existing user
        else:
            # Insert the user with a default initial balance of 0.00
            cur.execute("INSERT INTO users (username, password, account_number, current_balance) VALUES (%s, %s, %s, %s)",
                        (username, hashed_password, account_number, 0.00))
            print("User signed up")
            return jsonify({"message": "Signup successful. You can now login."}), 200  # Return JSON response for successful signup
    else:
        return render_template("signup.html")


# Function to handle the login page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

        # Hash password for comparison
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, hashed_password))
        existing_user = cur.fetchone()

        if existing_user:
            return render_template("BANKHOME.html")
        else:
            return "Invalid username or password, Please enter valid credentials"
    else:
        return render_template("BANKLOGIN.html")


@app.route("/deposit", methods=["POST", "GET"])
def deposit():
    if request.method == 'POST':
        account_number = request.form.get('account_number')
        amount = float(request.form['amount'])

        # Check if the account number exists in the users table
        cur.execute("SELECT EXISTS(SELECT 1 FROM users WHERE account_number = %s)", (account_number,))
        account_exists = cur.fetchone()[0]

        if account_exists:
            # Update the account balance
            cur.execute("UPDATE users SET current_balance = current_balance + %s WHERE account_number = %s",
                        (amount, account_number))
            print("Account balance updated after deposit")

            # Insert a record into the transactions table with transaction_type set to lowercase
            cur.execute(
                "INSERT INTO transactions (user_id, transaction_type, amount, transaction_date) VALUES ((SELECT id FROM users WHERE account_number = %s), %s, %s, %s)",
                (account_number, 'deposit', amount, datetime.now()))
            print("Deposit transaction committed")

            return redirect("/")  # Redirect to the home page after deposit
        else:
            return "Account number not found"

    return render_template("Deposit.html")


# Function to handle withdrawing money
@app.route("/withdraw", methods=["POST", "GET"])
def withdraw():
    if request.method == 'POST':
        account_number = request.form.get('account_number')
        amount = decimal.Decimal(request.form['amount'])  # Convert amount to Decimal

        try:
            # Check if the account number exists in the users table
            cur.execute("SELECT EXISTS(SELECT 1 FROM users WHERE account_number = %s)", (account_number,))
            account_exists = cur.fetchone()[0]

            if not account_exists:
                return "Account number not found"

            # Check balance
            cur.execute("SELECT current_balance FROM users WHERE account_number = %s", (account_number,))
            result = cur.fetchone()

            if result:
                current_balance = result[0]
                if current_balance >= amount:
                    # Update the account balance
                    new_balance = current_balance - amount
                    cur.execute("UPDATE users SET current_balance = %s WHERE account_number = %s",
                                (new_balance, account_number))
                    print("Account balance updated after withdrawal")

                    # Insert a record into the transactions table
                    cur.execute(
                        "INSERT INTO transactions (user_id, transaction_type, amount, transaction_date) VALUES ((SELECT id FROM users WHERE account_number = %s), %s, %s, %s)",
                        (account_number, 'withdrawal', amount, datetime.now()))
                    print("Withdrawal transaction committed")

                    # Commit changes to the database
                    conn.commit()

                    return f"Withdrawal successful. Remaining balance: {new_balance}"
                else:
                    return "Insufficient funds"
            else:
                return "Error occurred while retrieving account balance"
        except Exception as e:
            traceback.print_exc()  # Print the exception traceback
            return "An error occurred while processing the withdrawal."

    return render_template("Withdraw.html")


# Function to generate mini statement
# Function to generate mini statement
# Function to generate mini statement
@app.route("/mini_statement", methods=["GET", "POST"])
def mini_statement():
    if request.method == "POST":
        try:
            account_number = request.form.get('account_number')
            from_date = request.form.get('from_date')
            to_date = request.form.get('to_date')
            export_type = request.form.get('export_type')

            # Convert from_date and to_date to datetime objects
            from_date = datetime.strptime(from_date, "%Y-%m-%d")
            to_date = datetime.strptime(to_date, "%Y-%m-%d")

            # Check if the date range is within the allowed limit (3 months or 6 months)
            allowed_delta = timedelta(days=90) if request.form.get('time_period') == '3_months' else timedelta(days=180)

            if to_date - from_date > allowed_delta:
                return "Date range exceeds the allowed limit"

            # Calculate the end date of the allowed range
            allowed_to_date = from_date + allowed_delta

            cur.execute(
                "SELECT t.ID, u.account_number, t.amount, t.transaction_type, t.transaction_date, u.current_balance FROM transactions t INNER JOIN users u ON t.user_id = u.ID WHERE t.transaction_date BETWEEN %s AND %s",
                (from_date, allowed_to_date))
            transactions = cur.fetchall()

            if not transactions:
                return "No transactions found within the specified date range"

            if export_type == 'pdf':
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                
                # Set column widths
                col_widths = [25, 30, 25, 30, 55, 30]

                # Add column headers
                headers = ['Transaction ID', 'Account Number', 'Amount', 'Transaction Type', 'Transaction Date', 'Balance']
                for i, header in enumerate(headers):
                    font_size = 14 if len(header) <= 12 else 8  # Adjust font size dynamically
                    pdf.set_font("Arial", size=font_size)
                    pdf.cell(col_widths[i], 10, header, border=1)
                pdf.ln()

                # Add transaction details
                for transaction in transactions:
                    for i in range(len(transaction)):
                        pdf.cell(col_widths[i], 10, str(transaction[i]), border=1)
                    pdf.ln()

                pdf_data = pdf.output(dest='S').encode('latin1')
                return Response(pdf_data, mimetype='application/pdf',
                                headers={'Content-Disposition': 'attachment; filename=mini_statement.pdf'})
            elif export_type == 'csv':
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(['Transaction ID', 'Account Number', 'Amount', 'Transaction Type', 'Transaction Date', 'Balance'])
                for transaction in transactions:
                    writer.writerow(transaction)
                csv_data = output.getvalue()
                return Response(csv_data, mimetype='text/csv',
                                headers={'Content-Disposition': 'attachment; filename=mini_statement.csv'})
            else:
                return "Invalid export type", 400
        except Exception as e:
            traceback.print_exc()  # Print the exception traceback
            return "An error occurred while generating the mini statement. Please try again later."
    else:
        return render_template("MINISTATE.HTML")


@app.route("/statement", methods=["GET", "POST"])
def statement():
    if request.method == "POST":
        account_number = request.form.get('account_number')
        export_type = request.form.get('export_type')

        cur.execute(
            "SELECT t.ID, u.account_number, t.amount, t.transaction_type, t.transaction_date, u.current_balance FROM transactions t INNER JOIN users u ON t.user_id = u.ID WHERE u.account_number = %s",
            (account_number,))
        transactions = cur.fetchall()

        if export_type == 'pdf':
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            # Set column widths
            col_widths = [25, 30, 25, 30, 55, 30]

            # Add column headers
            headers = ['Transaction ID', 'Account Number', 'Amount', 'Transaction Type', 'Transaction Date', 'Balance']
            for i, header in enumerate(headers):
                font_size = 12 if len(header) <= 12 else 8  # Adjust font size dynamically
                pdf.set_font("Arial", size=font_size)
                pdf.cell(col_widths[i], 10, header, border=1)
            pdf.ln()

            # Add transaction details
            for transaction in transactions:
                for i in range(len(transaction)):
                    pdf.cell(col_widths[i], 10, str(transaction[i]), border=1)
                pdf.ln()

            pdf_data = pdf.output(dest='S').encode('latin1')
            return Response(pdf_data, mimetype='application/pdf',
                            headers={'Content-Disposition': 'attachment; filename=statement.pdf'})
        elif export_type == 'csv':
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['Transaction ID', 'Account Number', 'Amount', 'Transaction Type', 'Transaction Date', 'Balance'])
            for transaction in transactions:
                writer.writerow(transaction)
            csv_data = output.getvalue()
            return Response(csv_data, mimetype='text/csv',
                            headers={'Content-Disposition': 'attachment; filename=statement.csv'})
        else:
            return "Invalid export type", 400
    else:
        return render_template("statement.html")

# Function to check username availability
@app.route("/check_username_availability", methods=["POST"])
def check_username_availability():
    username = request.form.get('username')

    cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    existing_user = cur.fetchone()

    if existing_user:
        return "exists"
    else:
        return "available"


if __name__ == "__main__":
    app.run(debug=True)
