import requests
import pandas as pd
import smtplib
from datetime import datetime
from email.message import EmailMessage

import html
#import win32com.client as win32

SMTP_SERVER = "smtp"
SMTP_PORT = 25
MAIL_FROM = ""
MAIL_TO = ""
SUBJECT = "Zabbix PreProd report"

results = []
HOST_THRESHOLD_DAYS = 30
#info for zabbixes

zabbixes = [
    {
		"name": "PCI PROD",
        "url": "",
        "api_token": ""
	},
	{
		"name": "Non-PCI PROD",
        "url": "",
        "api_token": ""
	}
]

#func for getting the oldes item

def get_oldest_item_date(zabbix, hostid):
    items = api_call(
        zabbix,
        "item.get",
        {
            "hostids": hostid,
            "output": ["itemid", "value_type"]
        }
    )

    oldest = None

    for item in items:

        trends = api_call(
            zabbix,
            "trend.get",
            {
                "itemids": item["itemid"],
                "sortfield": "clock",
                "sortorder": "ASC",
                "limit": 1
            }
        )

        if trends:
            clock = int(trends[0]["clock"])

        else:
            history = api_call(
                zabbix,
                "history.get",
                {
                    "history": item["value_type"],
                    "itemids": item["itemid"],
                    "sortfield": "clock",
                    "sortorder": "ASC",
                    "limit": 1
                }
            )

            if not history:
                
                continue

            clock = int(history[0]["clock"])

        if oldest is None or clock < oldest:
            oldest = clock
    if not oldest:
        return f"No trend or history"

    return datetime.fromtimestamp(oldest)

#api call from zabbix documentory
def api_call(zabbix, method, params):
    headers = {
        "Content-Type": "application/json-rpc",
        "Authorization": f"Bearer {zabbix['api_token']}"
    }

    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }

    response = requests.post(
        zabbix["url"],
        headers=headers,
        json=payload,
        verify=False
    )

    response.raise_for_status()

    result = response.json()

    if "error" in result:
        raise Exception(result["error"])

    return result["result"]

#getting hosts from the current hostgroup
def get_hostgroup(zabbix, group_name):
    groups = api_call(
        zabbix,
        "hostgroup.get",
        {
            "output": ["groupid", "name"],
            "filter": {
                "name": [group_name]
            }
        }
    )

    return groups[0] if groups else None

#finding hosts by name 
def find_hosts(zabbix, search_by, value):
    params = {
        "output": [
            "hostid",
            "host",
            "name"
        ],
        "selectHostGroups": [
            "groupid",
            "name"
        ]
    }

    if search_by == "name":
        params["filter"] = {
            "host": [value]
        }

    elif search_by == "hostgroup":
        params["groupids"] = [
            get_hostgroup(
                zabbix,
                value
            )["groupid"]
        ]

    else:
        raise ValueError(
            f"Unsupported search type: {search_by}"
        )

    return api_call(
        zabbix,
        "host.get",
        params
    )

#going through zabbixes
for zabbix in zabbixes:
    print(f"Processing Zabbix: {zabbix['name']}")

    hosts = find_hosts(zabbix, "hostgroup", "PreProd")

    if not hosts:
        print("No hosts found in PreProd.")
        continue

    for host in hosts:
        host_groups = host["hostgroups"]

        # you dont need this!!! i was testing something!!!
        # if len(host_groups) > 2:
        #     continue

        oldest_date = get_oldest_item_date(
            zabbix,
            host["hostid"]
        )
        #cheking if there is date
        if oldest_date != "No trend or history":
            days = (datetime.now() - oldest_date).days
            first_item = oldest_date.strftime("%d-%m-%Y %H:%M:%S")
        else:
            continue
        
        if int(days) > HOST_THRESHOLD_DAYS:
            results.append({
                "Zabbix": zabbix["name"],
                "Host ID": host["hostid"],
                "Hostname": host["host"],
                "Visible Name": host["name"],
                "First Item": first_item,
                "Days in PreProd": days 
        })



if not results:
    print("No data found.")
    exit()

df = pd.DataFrame(results)

df = df.sort_values(
    by=["Zabbix", "Days in PreProd"],
    ascending=[True, False]
)
# creating the html file for test reasons
# file_name = rf"C:\something\something\PreProd_Hosts_{datetime.now().strftime('%d-%m-%Y')}.html"

generated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

html_report = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>PreProd Report</title>

<style>

body {{
    font-family: Arial, Helvetica, sans-serif;
    margin: 20px;
    color: #222;
}}

.generated-time {{
    font-size: 16px;
    color: #555;
    background-color: #f2f2f2;
    padding: 12px 16px;
    margin-bottom: 20px;
    border-radius: 8px;
}}

.group-title {{
    font-size: 22px;
    font-weight: bold;
    margin-top: 25px;
    margin-bottom: 10px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 25px;
}}

th {{
    text-align: left;
    padding: 10px;
    border-bottom: 2px solid #c8c8c8;
    background-color: #f2f2f2;
}}

td {{
    padding: 9px;
    border-bottom: 1px solid #d7dadb;
}}

tr:hover {{
    background-color: #ececec;
}}

</style>
</head>

<body>

<h1>PreProd Report</h1>

<div class="generated-time">
Generated: <strong>{generated_time}</strong>
</div>

<div>
<strong>Total hosts older than {HOST_THRESHOLD_DAYS} days:</strong>
{len(df)}
</div>

"""

for zabbix_name in df["Zabbix"].unique():

    group_df = df[df["Zabbix"] == zabbix_name]

    html_report += f"""
    <div class="group-title">
        {html.escape(zabbix_name)} ({len(group_df)} hosts)
    </div>

    <table>
        <thead>
            <tr>
                <th>Host ID</th>
                <th>Hostname</th>
                <th>Visible Name</th>
                <th>First Item</th>
                <th>Days in PreProd</th>
            </tr>
        </thead>
        <tbody>
    """

    for _, row in group_df.iterrows():

        html_report += f"""
        <tr>
            <td>{html.escape(str(row['Host ID']))}</td>
            <td>{html.escape(str(row['Hostname']))}</td>
            <td>{html.escape(str(row['Visible Name']))}</td>
            <td>{html.escape(str(row['First Item']))}</td>
            <td>{html.escape(str(row['Days in PreProd']))}</td>
        </tr>
        """

    html_report += """
        </tbody>
    </table>
    """

html_report += """
</body>
</html>
"""
#writting in the html file
# with open(file_name, "w", encoding="utf-8") as f:
#     f.write(html_report)

# print(f"HTML file created successfully: {file_name}")


subject = (
        f"Zabbix PreProd Report - "
    )

# for testing how does the email looks
# try:
#         outlook = win32.Dispatch("Outlook.Application")

#         mail = outlook.CreateItem(0)
#         mail.To = "your email"
#         mail.Subject = subject
#         mail.HTMLBody = html_report

#         mail.Send()

# except Exception as e:

#         print(
#             f"ERROR sending : {e}"
#         )


# sending the email
def send_email(
    smtp_server: str,
    smtp_port: int,
    mail_from: str,
    mail_to: str,
    subject: str,
    html: str,
):
    msg = EmailMessage()

    msg["From"] = mail_from
    msg["To"] = mail_to
    msg["Subject"] = subject

    msg.set_content(
        "This report contains HTML. "
        "Please view it in an HTML-capable email client."
    )

    msg.add_alternative(
        html,
        subtype="html"
    )

    with smtplib.SMTP(
        smtp_server,
        smtp_port,
        timeout=60
    ) as s:

        s.send_message(msg)

send_email(
    smtp_server=SMTP_SERVER,
    smtp_port=SMTP_PORT,
    mail_from=MAIL_FROM,
    mail_to=MAIL_TO,
    subject=SUBJECT,
    html=html_report
)
