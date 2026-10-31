# KLL Lost and Found — Setup Guide

Full step-by-step instructions for Windows. Follow these steps in order to get the project running on your laptop.

---

## 1. Get the Project on Your Laptop

Use **Command Prompt** (press the Windows key, type `cmd`, and press Enter).

### Step 1: Install the Required Tools

You need **Python 3.10+ (Python 3.13 recommended)**, **Git**, and (recommended) **VS Code**.

1. **Python:** Go to https://www.python.org/downloads/windows/ and download the 64-bit installer for Python 3.13.x.
   - **CRITICAL:** On the very first screen of the installer, **tick "Add python.exe to PATH"** at the bottom before clicking Install Now. This prevents `'python' is not recognized` errors.
2. **Git:** Download and install from https://git-scm.com/downloads with default settings.
3. **VS Code (Optional but recommended):** Download from https://code.visualstudio.com/.

Close Command Prompt, open a new one, and verify the tools:

```cmd
python --version
pip --version
git --version
```

Configure Git with your name and email (one time only):

```cmd
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

---

### Step 2: Clone the Repository

Keep the project in a short, local path like `C:\dev` (**do NOT put it inside OneDrive or Desktop**, as OneDrive locks database and virtual environment files).

```cmd
mkdir C:\dev
cd C:\dev
git clone https://github.com/Ceihiro/kll-lost-and-found.git
cd kll-lost-and-found
```

> **No Git?** You can click the green **Code** button on GitHub, select **Download ZIP**, and extract it into `C:\dev\kll-lost-and-found`. (Note: using `git clone` is better so you can `git pull` updates from teammates).

---

### Step 3: Create Your Virtual Environment & Install Dependencies

A virtual environment (`venv`) keeps project packages isolated. **Everyone creates their own on their machine. Never copy or commit a `venv` folder.**

```cmd
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
```

- When active, you will see `(venv)` at the beginning of your prompt line.
- If you use PowerShell and get a script execution policy error, switch to **Command Prompt (cmd)**.

---

### Step 4: Set Up the Environment File (.env)

The `.env` file holds sensitive configuration like staff credentials. Copy the example file:

```cmd
copy .env.example .env
```

Default credentials inside `.env`:
- **Username:** `staff`
- **Password:** `kll2026`

---

### Step 5: Check Installation & Seed Sample Data

Run the test script to ensure all libraries (Flask, scikit-learn, etc.) are installed properly:

```cmd
python test.py
```

If it prints version numbers and similarity scores with no errors, initialize the database with sample items:

```cmd
python seed_data.py
```

---

### Step 6: Run the App

Start the Flask local development server:

```cmd
python app.py
```

1. Open your browser and go to: **http://127.0.0.1:5000**
2. You will see the KLL Smart Find AI homepage with active lost reports and found items.
3. To stop the server at any time, go to the Command Prompt and press **Ctrl + C**.

---

## 2. Testing Features

1. **Student Report Lost:** Click **"Report Lost Item"** on the navbar, fill in the details, and submit. The system will immediately display the **AI Matches** ranked by similarity.
2. **Staff Login & Full CRUD:**
   - Click **"Staff Portal"** in the top navigation.
   - Log in with `staff` / `kll2026`.
   - On the **Staff Dashboard**, you can:
     - View KPI summary cards and Chart.js analytics graphs.
     - **Edit** any item's category, location, custody, or status.
     - **Delete** invalid or duplicate reports.
     - Review **AI Matching Weight Refinement** learned from verified claims.
     - **Export CSV** of all inventory records.
3. **AI Accuracy Benchmark:**
   Run the evaluation script to test Top-1 and Top-3 accuracy across 22 lost and 27 found benchmark reports:
   ```cmd
   python evaluate.py
   ```

---

## 3. Daily Team Workflow

Every time you sit down to work:

```cmd
cd C:\dev\kll-lost-and-found
venv\Scripts\activate
git pull
python app.py
```

When you finish your changes:

```cmd
git add .
git commit -m "Describe what you updated"
git push origin main
```

---

## 4. Troubleshooting Guide

| Problem | Cause & Fix |
|---|---|
| `'python' is not recognized` or Microsoft Store opens | Python was not added to PATH. Rerun the Python installer, select **Modify**, and check **"Add python.exe to PATH"**. |
| `No module named 'flask'` | Your virtual environment is not active. Run `venv\Scripts\activate` first. |
| `(venv)` is missing from prompt | You forgot to activate it. Run `cd C:\dev\kll-lost-and-found` then `venv\Scripts\activate`. |
| `can't open file 'app.py': [Errno 2] No such file or directory` | You are in the wrong directory. Run `cd C:\dev\kll-lost-and-found`. |
| `Address already in use` (Port 5000) | Another copy of `app.py` is already running. Close the previous Command Prompt window or press **Ctrl + C**. |
| `git clone` fails with 403 or password error | The repository is private. Ask the project owner to invite your GitHub account as a collaborator. |
| Staff login says "Incorrect username or password" | Ensure you created `.env` by running `copy .env.example .env`. Default login is `staff` / `kll2026`. |
| PowerShell blocks `activate.ps1` | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` in PowerShell, or simply use Command Prompt (`cmd.exe`). |
