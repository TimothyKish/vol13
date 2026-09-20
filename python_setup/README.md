🛠️ Environment Build Guide: Resolving Wheel Dependencies
If you are setting up this project and encounter an error like Microsoft Visual C++ 14.0 or greater is required during the pip install phase, your system is missing the necessary C++ compiler to build performance-critical libraries from source.

Step 1: Install Microsoft C++ Build Tools
To build the required wheels locally, you must have the Microsoft C++ Build Tools installed on your system.

Download: Visit the official Microsoft C++ Build Tools page.

Run Installer: Launch the vs_buildtools.exe installer.

Select Workload: In the installer, ensure you check the box for "Desktop development with C++".

Note: This is a heavy installation (several GBs); ensure you have sufficient disk space.

Install: Click Install and wait for the process to complete.

Restart: Once finished, restart your terminal/Git Bash to ensure the new path variables are picked up.

Step 2: Verification and Installation
After installing the build tools, navigate to the root of the cloned repository and run the installation command:

Bash
# Ensure your virtual environment is active
source venv/Scripts/activate

# Install dependencies from the root manifest
pip install -r requirements.txt
Step 3: Troubleshooting "Ghost" Cache Errors
If you previously attempted a build and it failed, your local Git/Pip cache may be "stuck" on a corrupted state. If the install fails again, clear your cache before retrying:

Clear Pip Cache:

Bash
pip cache purge
Clear Local Metadata:
If you see errors referencing Reactivating local git directory or branch yet to be born, ensure your directory is clean:

Bash
# Only if you suspect a corrupt submodule cache
rm -rf .git/modules/src/Unification/<vol_name>