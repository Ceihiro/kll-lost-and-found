# Setup guide

Full step-by-step instructions for Windows.

\---

## Get the project on your laptop

Do these steps in order. Use **Command Prompt** (press the Windows key, type `cmd`, press Enter).

### Step 1: Install the tools

You need Python 3.13, Git, and (recommended) VS Code.

1. **Python 3.13:** go to https://www.python.org/downloads/windows/ and under **Stable Releases** choose **Python 3.13.x** and click **Windows installer (64-bit)**.
   - On the first screen of the installer, **tick "Add python.exe to PATH"** at the bottom. This is the most common mistake.
   - Then click **Install Now**.
   - Use 3.13, not the newest version. Brand-new Python versions can be missing library support.

2. **Git:** https://git-scm.com/downloads. Install with the default options.
3. **VS Code (editor):** https://code.visualstudio.com/. After installing, open it, go to Extensions, and install the **Python** extension.

Close Command Prompt, open a new one, and check:

```
python --version
pip --version
git --version
```

Each command should print a version number (Python should say 3.13.x). If it says `'python' is not recognized`, or opens the Microsoft Store, Python is not installed correctly. Run the Python installer again, choose **Modify** or **Repair**, and tick "Add python.exe to PATH".

Tell Git who you are (one time only):

```
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

### Step 2: Clone the repository

Keep the project in a short folder like `C:\\dev`, **not** on the Desktop and **not** inside OneDrive. OneDrive can lock the many small files inside the virtual environment and cause strange errors.

```
mkdir C:\\dev
cd C:\\dev
git clone https://github.com/Ceihiro/kll-lost-and-found.git
cd findit-ai
```

You now have the project in `C:\\dev\\findit-ai`.

> \*\*No Git?\*\* On the repository page click the green \*\*Code\*\* button, then \*\*Download ZIP\*\*, and unzip it into `C:\\dev`. This works for running the app, but you cannot `git pull` or `git push` updates without Git.

### Step 3: Create your own virtual environment and install the libraries

A virtual environment (venv) keeps this project's libraries separate from the rest of your laptop. **Everyone makes their own. Never copy someone else's `venv` folder.**

```
python -m venv venv
venv\\Scripts\\activate
python -m pip install -r requirements.txt
```

- After the second command you should see `(venv)` at the start of the line.
- The install takes a few minutes the first time.
- If you use PowerShell and the activate command is blocked, use Command Prompt (cmd) instead.

### Step 4: Check that everything works

```
python test.py
```

You should see a row of three numbers (about `1.0  0.63  0.0`) and a line with the Flask, pandas, and scikit-learn versions. A harmless warning about `flask.\_\_version\_\_` may appear. If you see the numbers, your setup is complete.

### Step 5: Run the app

```
python seed\_data.py
python app.py
```

- `seed\_data.py` adds 7 sample found items. Run it **once** (optional).
- Open **http://127.0.0.1:5000** in your browser. You should see the home page with the lost and found lists.
- To stop the app, click the Command Prompt window and press **Ctrl + C**.

### Step 6: Try it

1. Click **I lost something**.
2. Choose Calculator, Black, room Lab 2, and write the description `black calculator`.
3. Click **Find possible matches**. The black scientific calculator found in Lab 2 should be ranked #1, with its score and reasons.

\---

## Working on the project

Every time you start working, open a new Command Prompt and run:

```
cd C:\\dev\\findit-ai
venv\\Scripts\\activate
git pull
```

- `venv\\Scripts\\activate` must be run **every time** you open a new terminal. If you forget, you will get `No module named 'flask'`.
- `git pull` downloads your teammates' latest work. Do it before you start.

When you finish a piece of work:

```
git add .
git commit -m "short message about what you changed"
git push
```

Good habits:

- Pull before you start, and push often, so changes do not pile up.
- Mostly edit your own files, to avoid conflicts.
- If you add a new library, run `pip freeze > requirements.txt` and push it so everyone can install the same libraries.
- Never upload the `venv` folder or the `findit.db` database. The `.gitignore` file already prevents this.

## Troubleshooting

| Problem                                                    | Fix                                                                                                                                          |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `'python' is not recognized`, or the Microsoft Store opens | Python is not installed, or "Add python.exe to PATH" was not ticked. Run the Python installer again and choose Modify or Repair.             |
| `'pip' is not recognized`                                  | Same cause. Use `python -m pip ...` or fix the Python install.                                                                               |
| `No module named 'flask'`                                  | Your venv is not active or the libraries are not installed. Run `venv\\Scripts\\activate`, then `python -m pip install -r requirements.txt`. |
| `(venv)` does not show                                     | Run `cd C:\\dev\\findit-ai`, then `venv\\Scripts\\activate`.                                                                                 |
| `can't open file ... app.py`                               | You are in the wrong folder. Run `cd C:\\dev\\findit-ai`.                                                                                    |
| Activate is blocked in PowerShell                          | Use Command Prompt (cmd) instead.                                                                                                            |
| `pip install` fails or is very slow                        | Check your internet, and make sure you use Python 3.13.                                                                                      |
| `python --version` shows the wrong version                 | Run `where python`. The first line is the one that runs. With `(venv)` active it should point inside the `venv` folder.                      |
| Strange permission errors in `venv`                        | The project is inside OneDrive. Move it to `C:\\dev` and create a new venv.                                                                  |
| Moved the project and the venv stopped working             | A venv remembers where it was created. Delete the `venv` folder (`rmdir /s /q venv`) and create a new one.                                   |
| `git clone` asks for a password or fails with "not found"  | The repository is private. Ask the team lead to add you, accept the email invitation, and sign in with the browser window Git opens.         |
| `git push` is rejected                                     | Someone pushed first. Run `git pull`, then `git push` again.                                                                                 |
| Port 5000 is already in use                                | An older copy of the app is still running. Close its Command Prompt window, or press Ctrl + C in it.                                         |
| The page does not load                                     | Check that `python app.py` is still running and open http://127.0.0.1:5000 (not https).                                                      |

\---

## Measuring how well it works

`evaluate.py` runs the matching on test files in the `data/` folder and prints top-1 and top-3 accuracy for three methods: attribute only, text only, and combined.

```
python evaluate.py
```

| File                      | What it contains                                                                  |
| ------------------------- | --------------------------------------------------------------------------------- |
| `data/lost\_reports.csv`  | Fake lost reports (id, category, color, brand, description, location, event_time) |
| `data/found\_reports.csv` | Fake found reports (same columns)                                                 |
| `data/true\_matches.csv`  | The correct answers (lost_id, found_id)                                           |

The sample files have only 5 lost and 7 found reports, and every method scores 100% because the cases are easy. For the real evaluation, the group should write 50 to 100 reports with 30 to 40 known pairs, including harder cases: different wording for the same item, blank brands, different rooms, and look-alike items.
