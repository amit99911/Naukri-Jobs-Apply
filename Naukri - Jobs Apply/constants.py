# Configuration and constants used in the script. Update values as needed.

# ===== NAUKRI CREDENTIALS =====
USERNAME = "amit99911@live.com"
PASSWORD = "Reset@123"
MOBILE = "7795227944"

# ===== RESUME PATHS =====
ORIGINAL_RESUME_PATH = "C:/Users/amit.sinha.ext_littl/Downloads/Amit Sinha_Project Manager_12 Years_Nasdaq"
MODIFIED_RESUME_PATH = "C:/Users/amit.sinha.ext_littl/Downloads/Amit Sinha_Project Manager_12 Years_Nasdaq"

# ===== NAUKRI URLS =====
NAUKRI_LOGIN_URL = "https://www.naukri.com/nlogin/login"
NAUKRI_PROFILE_URL = "https://www.naukri.com/mnjuser/profile"
NAUKRI_RECOMMENDED_JOBS_URL = "https://www.naukri.com/mnjuser/homepage"

# ===== JOB APPLICATION SETTINGS =====
BATCH_SIZE = 5  # Number of jobs to apply per batch
MAX_BATCHES = 0  # Maximum number of batches to process (set to 0 for unlimited)
DELAY_BETWEEN_APPLICATIONS = (2, 4)  # Random delay in seconds (min, max)
DELAY_BETWEEN_BATCHES = (30, 60)  # Delay between batches in seconds (min, max)

# ===== AUTO-FILL SETTINGS =====
AUTO_FILL_ENABLED = True
SKIP_ALREADY_APPLIED = True

# ===== BROWSER SETTINGS =====
HEADLESS_MODE = False
IMPLICIT_WAIT = 5
EXPLICIT_WAIT = 15

# ===== RESUME MODIFICATION =====
UPDATE_PDF_WITH_HIDDEN_TEXT = False
