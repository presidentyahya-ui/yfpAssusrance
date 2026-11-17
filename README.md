# YFP Assurance: website with an easy editor

Once set up, you edit everything from a dashboard in your browser:

**`https://yfp-assurance.com/admin`** → *Login with GitHub* → edit → **Publish**. The live site updates in about 1–2 minutes.

From the dashboard you can:

| Section | What you can do |
|---|---|
| **Equipment Listings** | Add a machine, upload photos, set price and status (Available / Reserved / Sold), hide or delete |
| **Website Pages** | Change any headline, paragraph, list, button text or image on every page. Add, remove or reorder categories (factory-direct products, equipment categories, project types), steps and cards |
| **Settings & Contact** | Email, phone, WhatsApp, hours, form service, prices, Digital CV ordering on/off, Skills Mirror links, analytics, footer legal line |

The layout and design are locked, so you can't accidentally break the look of the site.

---

## One-time setup (about 20–30 minutes)

You need two free accounts: **GitHub** (stores the website files and gives you a secure login) and **Cloudflare** (hosts the site). Neither needs a credit card for this setup.

### Step 1: Put the files on GitHub
All project files are in **one flat folder, with no subfolders**, so they upload in one go.
1. Create a free account at <https://github.com>.
2. Click **+ → New repository**. Name it `yfp-assurance`, choose **Private**, then click **Create repository**.
3. On the new repository page, click **uploading an existing file**.
4. Click **choose your files**, open the unzipped folder, select **all** the files (Ctrl+A on Windows, Cmd+A on Mac) and click **Open**. Dragging all the files into the page works too.
5. Wait until all 47 files are listed, then click **Commit changes**.

The order doesn't matter. Two folders, `listings` and `uploads`, will be created automatically later, when you add your first machine or photo in the editor.

### Step 2: Create the website on Cloudflare Pages
1. Create a free account at <https://dash.cloudflare.com>.
2. Go to **Workers & Pages → Create → Pages → Connect to Git**, then connect your GitHub account and choose `yfp-assurance`.
3. Build settings:
   - Framework preset: **None**
   - Build command: **`python3 build.py`**
   - Build output directory: **`dist`**
4. Click **Save and Deploy**. After a minute, your site is live at an address like `https://yfp-assurance.pages.dev`. Note this address down.

### Step 3: Create the editor login (GitHub OAuth App)
1. On GitHub, go to your profile picture → **Settings → Developer settings → OAuth Apps → New OAuth App**.
2. Fill in:
   - Application name: `YFP Assurance Editor`
   - Homepage URL: `https://yfp-assurance.pages.dev` (your address from Step 2)
   - Authorization callback URL: `https://yfp-assurance.pages.dev/api/callback`
3. Click **Register application**. Copy the **Client ID**, then click **Generate a new client secret** and copy the secret.

### Step 4: Connect the login to the website
In Cloudflare: your Pages project → **Settings → Variables and Secrets** → add these for **Production**:

| Name | Value | Type |
|---|---|---|
| `GITHUB_CLIENT_ID` | the Client ID from Step 3 | Text |
| `GITHUB_CLIENT_SECRET` | the client secret from Step 3 | **Secret** |
| `CMS_REPO` | `your-github-username/yfp-assurance` | Text |

Then go to **Deployments → ⋯ on the latest deployment → Retry deployment** so the settings take effect.

### Step 5: Log in
Open `https://yfp-assurance.pages.dev/admin` → **Login with GitHub** → **Authorize**. You're in.

Start with **Settings & Contact** and fill in your email, phone and WhatsApp.

### Step 6: Connect your domain (when ready)
1. Confirm you own `yfp-assurance.com`, or register it. Cloudflare Registrar sells domains at cost.
2. Cloudflare Pages project → **Custom domains → Set up a custom domain** → `yfp-assurance.com`, then repeat for `www.yfp-assurance.com`.
   - If the domain is registered elsewhere, Cloudflare will show you the DNS change or nameservers to set at your registrar.
3. **Update the GitHub OAuth App** (Step 3) to use the new address:
   - Homepage URL: `https://yfp-assurance.com`
   - Callback URL: `https://yfp-assurance.com/api/callback`
4. From then on, log in at `https://yfp-assurance.com/admin`.
5. In **Settings & Contact**, make sure *Website address* is `https://yfp-assurance.com`.

> The editor login works only on the address registered in the OAuth App. If you need both the pages.dev address and your domain, create a second OAuth App for the other address.

---

## Everyday use

**Add a machine for sale:** Equipment Listings → **New Machine** → fill in the reference, name, category, price and status → drag in photos → **Publish → Publish now**.

**Mark a machine sold:** open it → Status: **Sold** → Publish. To remove it from the site completely, switch off *Show on website*, or delete it.

**Change text on a page:** Website Pages → choose the page → open the section → edit → Publish.

**Add a factory-direct category:** Website Pages → Factory Direct → *Product categories* → **Add** → fill in the name, description, typical applications and photo → Publish. The category's section, jump link and quote-form option are all created automatically. Drag categories to reorder them. Tick **Feature this category** to make one the large dark block at the top.

**Give someone else editing access:** on GitHub, open the repository → **Settings → Collaborators → Add people**. They log in at `/admin` with their own GitHub account. Only people you add can save changes.

Photos: JPG or WebP, about 1600 px wide, under 400 KB. Use a free tool such as squoosh.app to shrink large photos before uploading.

---

## Before going live: checklist

1. Contact email, phone and WhatsApp (Settings & Contact).
2. **Form service:** create a free Web3Forms access key at web3forms.com using your inquiry email. Then set Settings → Form service: `web3forms` and paste the key. Until then, forms offer visitors a prefilled email/WhatsApp message and never claim to have sent anything.
3. Replace the placeholder images. Each one is labelled "PLACEHOLDER IMAGE".
4. Digital CV: keep *Orders open* OFF until regulatory compliance is confirmed.
5. Have the privacy notice reviewed (Website Pages → Privacy Notice).
6. Add your registered company name and licence number to the footer legal line if required (Settings & Contact → Footer & Skills Mirror section).
7. Connect your domain and update the OAuth App (Step 6).
8. Submit `https://yfp-assurance.com/sitemap.xml` to Google Search Console.

---

## For a developer (technical notes)

- **Flat layout:** every source file sits in the repository root.
  - Content: `settings.json`, `shared.json`, `page-*.json`. The editor adds `listings/` (one JSON per machine) and `uploads/` (media).
  - Assets: `styles.css`, `main.js`, `favicon.svg`, `*.svg` and `*.png` placeholders.
  - `worker.js`: Cloudflare Pages advanced-mode worker. It is copied to `dist/_worker.js`, serves assets via `env.ASSETS`, handles the GitHub OAuth for Decap CMS at `/api/auth` and `/api/callback`, and adds security headers.
- `build.py`: Python 3.8+, standard library only. It arranges the flat files into `dist/` (`css/`, `js/`, `images/`, `images/uploads/`, `admin/`) and generates the pages, `js/config.js`, `js/listings.js`, sitemap, robots and the editor config. The editor forms come from `SCHEMA` in `build.py`.
- Local preview: `python3 build.py && python3 -m http.server 8000 -d dist`. The `/api/*` login only works on Cloudflare.
- Local editing without GitHub: run `npx decap-server` in this folder, then open `http://localhost:8000/admin`.
