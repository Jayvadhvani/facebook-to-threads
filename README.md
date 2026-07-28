# Facebook to Threads Auto Poster

A lightweight, zero-maintenance Python script running on GitHub Actions that automatically copies posts from a Facebook Page to your Threads account every 15 minutes.

## Features
- **Fully Automated:** Runs every 15 minutes using GitHub Actions (completely free, no VPS or hosting required).
- **Duplicate Prevention:** Tracks the last posted Facebook ID in `last_post.json` and updates it dynamically.
- **Carousel Support:** Automatically maps single-image, text-only, and multi-image posts to Threads.
- **Auto Token Refreshing:** Automatically refreshes the 60-day Threads access token every 7 days and updates your repository variable dynamically.

---

## Repository Structure
- `.github/workflows/post.yml` — Runs the workflow every 15 minutes.
- `app.py` — The core logic connecting the Facebook Graph API to the Threads API.
- `config.py` — Maps environment variables to configuration settings.
- `last_post.json` — Stores state to prevent posting duplicates.
- `requirements.txt` — Project dependencies (`requests`).

---

## Setup Instructions

### Step 1: Create a GitHub Repository Variable
1. In your GitHub repository, go to **Settings** > **Secrets and variables** > **Actions** > **Variables**.
2. Click **New repository variable**.
3. Name it `THREADS_ACCESS_TOKEN` and paste your initial **Threads Access Token** into it.

### Step 2: Add Secrets to GitHub
Go to **Settings** > **Secrets and variables** > **Actions** > **Secrets** > **New repository secret** and add the following:
- `FB_PAGE_ID` — Your Facebook Page ID.
- `FB_PAGE_ACCESS_TOKEN` — Your Facebook Page Access Token.
- `THREADS_USER_ID` — Your Threads User ID.
- `THREADS_APP_SECRET` — Your Threads App Secret.

### Step 3: Run the Auto Poster
The workflow runs automatically every 15 minutes. To trigger a test run immediately:
1. Go to your repository on GitHub.
2. Click on the **Actions** tab.
3. Select **Facebook to Threads Auto Poster** on the left.
4. Click **Run workflow** -> **Run workflow**.
