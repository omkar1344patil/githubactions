import requests
import pandas as pd
from fpdf import FPDF
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Smartlead API Configuration
API_KEY = "6da7ff00-fd6b-440c-8915-5dbc582ec60c_de172e5"
offset = 0
limit = 100
url = f'https://server.smartlead.ai/api/v1/email-accounts/?api_key={API_KEY}&offset={offset}&limit=100'
all_data = []

# Fetching email accounts from API
while True:
    response = requests.get(f'https://server.smartlead.ai/api/v1/email-accounts/?api_key={API_KEY}&offset={offset}&limit=100')
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}, {response.text}")
        break
    
    data = response.json()  # Convert response to JSON
    all_data.extend(data)  # Add new data to the list

    if len(data) < limit:
        break  # If less than 100 objects returned, we reached the end
    
    offset += limit  # Move to the next batch

# Lists to store categorized data
no_of_acc = len(all_data)
rep_100 = []
rep_90_99 = []
rep_less_than_90 = []
inactive_warmup = []

# Processing data
for n in range(len(all_data)):
    rep = int(all_data[n]["warmup_details"]["warmup_reputation"].strip('%'))  # Convert "77%" to int
    warmup_status = all_data[n]["warmup_details"]["status"]
    from_email = all_data[n]["from_email"]

    entry = {"Email": from_email, "Warmup Status": warmup_status, "Reputation": rep}

    if rep == 100 and warmup_status == 'ACTIVE':
        rep_100.append(entry)
    elif 90 <= rep < 100 and warmup_status == 'ACTIVE':
        rep_90_99.append(entry)
    elif rep < 90 and warmup_status == 'ACTIVE':
        rep_less_than_90.append(entry)
    elif warmup_status != 'ACTIVE':
        inactive_warmup.append(entry)

# Creating DataFrames
df_rep_100 = pd.DataFrame(rep_100)
df_rep_90_99 = pd.DataFrame(rep_90_99)
df_rep_less_than_90 = pd.DataFrame(rep_less_than_90)
df_inactive_warmup = pd.DataFrame(inactive_warmup)

# Create PDF class
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 11)
        self.cell(200, 10, "Email Warmup Report", ln=True, align="C")
        self.ln(10)

    def chapter_title(self, title):
        self.set_font("Arial", "B", 9)
        self.cell(0, 10, title, ln=True, align="L")
        self.ln(5)

    def chapter_body(self, df):
        self.set_font("Arial", "", 7)
        if df.empty:
            self.cell(0, 10, "No records found.", ln=True)
        else:
            col_width = self.w / 3.5  # Adjust column width
            self.cell(col_width, 5, "Email", border=1, align="C")
            self.cell(col_width, 5, "Warmup Status", border=1, align="C")
            self.cell(col_width, 5, "Reputation", border=1, align="C")
            self.ln()
            for _, row in df.iterrows():
                self.cell(col_width, 5, row["Email"], border=1)
                self.cell(col_width, 5, row["Warmup Status"], border=1, align="C")
                self.cell(col_width, 5, str(row["Reputation"]), border=1, align="C")
                self.ln()
        self.ln(5)

# Initialize PDF
pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

# Add total count summary
pdf.set_font("Arial", "B", 9)
pdf.cell(0, 10, f"Total Number of Email Accounts: {no_of_acc}", ln=True)
pdf.ln(10)

# Add each section to PDF
pdf.chapter_title(f"Reputation 100% Emails (Count: {len(rep_100)})")
pdf.chapter_body(df_rep_100)

pdf.chapter_title(f"Reputation 90-99% Emails (Count: {len(rep_90_99)})")
pdf.chapter_body(df_rep_90_99)

pdf.chapter_title(f"Reputation <90% Emails (Count: {len(rep_less_than_90)})")
pdf.chapter_body(df_rep_less_than_90)

pdf.chapter_title(f"Inactive Warmup Emails (Count: {len(inactive_warmup)})")
pdf.chapter_body(df_inactive_warmup)

# Save PDF
pdf_filename = "email_warmup_report.pdf"
pdf.output(pdf_filename)

print(f"PDF report saved as {pdf_filename}")

# =========================== SLACK UPLOAD SECTION ===========================

# Slack Bot Token (Replace with your actual bot token)
SLACK_BOT_T = "xoxb-8291217244436-8504144024017-tcNhu7JfdggCzBmehQyIdM5d"
CHANNEL_ID = "C08ED3MLTEH"  # Replace with Slack channel ID or name

# Initialize Slack Client
client = WebClient(token=SLACK_BOT_T)

try:
    # Upload file using files_upload_v2()
    response = client.files_upload_v2(
        channel=CHANNEL_ID,  # List format required for v2
        file=pdf_filename,
        title="Email Warmup Report",
        initial_comment=f'''Here is the latest Inbox Reputation Report. \n{len(rep_100)} Inboxes are at 100% reputation [Good]. \n{len(rep_90_99)} Inboxes are at 90-90% reputation [Okay]. \n{len(rep_less_than_90)} Inboxes are at less than 90% reputation [Need Attention].'''
    )
    print("File uploaded successfully:", response["file"]["permalink"])
except SlackApiError as e:
    print(f"Error uploading file: {e.response['error']}")
