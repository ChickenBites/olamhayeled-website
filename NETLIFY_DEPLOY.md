# Deploy to Netlify

## Files for Netlify Deployment

### Structure
```
shira/
├── index.html              # Main page (updated with payment link)
├── billing-netlify.html   # Payment page (uses Netlify Functions)
├── netlify/
│   ├── functions/
│   │   └── payment.js    # Serverless API
│   └──.toml              # Netlify config
└── img/                   # Images
```

## Deploy Steps

### 1. Push to GitHub
```bash
cd /Users/shirlevyzinger/shira
git add .
git commit -m "Add billing system with Netlify Functions"
git push origin main
```

### 2. Connect to Netlify
1. Go to https://app.netlify.com
2. "Add new site" → "Import an existing project"
3. Select your GitHub repo
4. Build settings:
   - Build command: (empty)
   - Publish directory: .
   - Functions directory: netlify/functions

### 3. Deploy
Click "Deploy site"

## API Endpoints (Netlify Functions)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/.netlify/functions/payment/register` | POST | Register customer |
| `/.netlify/functions/payment/add-credit-card` | POST | Add credit card |
| `/.netlify/functions/payment/add-standing-order` | POST | Add standing order |
| `/.netlify/functions/payment/create-recurring` | POST | Create recurring payment |
| `/.netlify/functions/payment/config` | GET | Get config |

## Note on Data Storage

The current Netlify Function uses **in-memory storage** - data is lost when the function cold starts.

For production, add a database:
- **Supabase** (recommended) - Free tier
- **Airtable** - Free tier  
- **Firebase** - Free tier

Example with Supabase:
```javascript
// In payment.js, replace in-memory arrays with:
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_KEY;

// Then use:
const { data, error } = await supabase
  .from('customers')
  .insert([{ parent_name, phone, ... }]);
```

## Testing Locally

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Run local dev server
netlify dev
```

This will start both the static server and Netlify Functions at http://localhost:8888
