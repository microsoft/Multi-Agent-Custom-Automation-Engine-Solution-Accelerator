
"""Module for storing application-wide constants."""

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("MACAE_WEB_URL")
if URL and URL.endswith("/"):
    URL = URL[:-1]

API_URL = os.getenv("MACAE_URL_API")
if API_URL and API_URL.endswith("/"):
    API_URL = API_URL[:-1]

# Calculate HR start date (today + 10 days) and orientation date (today + 15 days)
hr_start_date = (datetime.today() + timedelta(days=10)).strftime("%m/%d/%Y")
hr_orientation_date = (datetime.today() + timedelta(days=15)).strftime("%m/%d/%Y")

# MACAE Input data
prompt_question1 = "onboard new employee"
hr_clarification_text = f"name: Peter parker, department: hr, role: manager, start date: {hr_start_date}, orientation date: {hr_orientation_date}, location: onsite, email: pp@contoso.com, mentor: Jim Shorts, benefits package: standard, ID Card: yes, salary: 70000, laptop- MacBook Pro"
