"""
Starter script: create a Daytona Sandbox ("project").

Setup:
1. Get an API key from https://app.daytona.io (Keys -> Create API Key)
2. Set it as an environment variable before running this script:
     PowerShell:  $env:DAYTONA_API_KEY = "your_api_key_here"
     Bash:        export DAYTONA_API_KEY=your_api_key_here
   (or copy .env.example to .env and fill it in - python-dotenv is already installed)
3. Run:  python create_project.py
"""

import os
from daytona import Daytona, DaytonaConfig

# Optional: load a local .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

api_key = os.environ.get("DAYTONA_API_KEY")
if not api_key:
    raise SystemExit(
        "DAYTONA_API_KEY is not set. Set it in your environment or in a .env file "
        "before running this script."
    )

daytona = Daytona(DaytonaConfig(api_key=api_key))

# Create a new sandbox
sandbox = daytona.create()
print(f"Created sandbox: {sandbox.id}")

# Run a quick smoke test inside it
response = sandbox.process.code_run('print("Hello from Daytona!")')
print("Output:", response.result)

# Clean up (comment this out if you want to keep the sandbox running)
sandbox.delete()
print("Sandbox deleted.")
