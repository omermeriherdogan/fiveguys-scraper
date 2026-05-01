# Publishing Checklist

Use this checklist before pushing the project to GitHub or sending it to a client.

## 1. Move The Project Outside OneDrive

For cleaner long runs, keep the working repo outside OneDrive, for example:

```powershell
C:\fiveguysscraper\scraper-v1
```

OneDrive can lock browser cache/profile folders and make cleanup painful.

## 2. Keep Source Control Clean

Commit source and documentation:

- `scraper.py`
- `README.md`
- `requirements.txt`
- `.gitignore`
- `examples/`
- `docs/`

Do not commit large scrape outputs unless a client specifically asks for them in the repository.

## 3. Initialize Git

```powershell
git init
git add scraper.py README.md requirements.txt .gitignore examples docs
git commit -m "Initial Five Guys scraper project"
```

## 4. Create A GitHub Repo

Option A: GitHub CLI

```powershell
gh repo create fiveguys-public-data-scraper --private --source . --remote origin --push
```

Option B: GitHub website

1. Create an empty repository on GitHub.
2. Copy the repository URL.
3. Run:

```powershell
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

## 5. Client Delivery

Recommended delivery package:

- GitHub repo with source/docs
- Separate `.zip` containing selected CSV/JSON outputs
- Short note with run date, region, review limit, concurrency, and failure count

Do not include disposable Chrome profiles, logs, debug folders, or virtualenv folders in the delivery zip.
