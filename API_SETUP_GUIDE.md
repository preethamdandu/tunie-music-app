# 🚀 API Setup Guide - 5 Minutes

Get TuneGenie running with FREE AI in 5 minutes!

## Step 1: Get API Keys (3 minutes)

### Required (Pick at least ONE):

#### Option A: Groq (Recommended - Fastest)
1. Go to: https://console.groq.com/keys
2. Sign up (free, no credit card)
3. Click "Create API Key"
4. Copy the key (starts with `gsk_`)

#### Option B: Google Gemini (Best Quality)
1. Go to: https://aistudio.google.com/apikey
2. Sign in with Google
3. Click "Get API Key"
4. Copy the key (starts with `AIza`)

#### Option C: OpenRouter (Most Flexible)
1. Go to: https://openrouter.ai/keys
2. Sign up (free, no credit card)
3. Click "Create Key"
4. Copy the key (starts with `sk-or-v1-`)

### Optional (More Capacity):

#### DeepSeek (Best Value)
1. Go to: https://platform.deepseek.com/api_keys
2. Sign up (free trial)
3. Create API key
4. Copy the key (starts with `sk-`)

#### HuggingFace (Fallback)
1. Go to: https://huggingface.co/settings/tokens
2. Sign in
3. Create new token
4. Copy the key (starts with `hf_`)

## Step 2: Configure TuneGenie (1 minute)

### Option A: Use Existing .env (Already Done!)
The `.env` file is already created with your keys. Just verify:

```bash
cat .env
```

### Option B: Create New .env
If you need to update keys:

```bash
# Copy example
cp env.example .env

# Edit with your keys
nano .env
```

Add your keys:
```bash
GROQ_API_KEY=gsk_your_key_here
GOOGLE_API_KEY=AIza_your_key_here
OPENROUTER_API_KEY=sk-or-v1-your_key_here
```

## Step 3: Install Dependencies (1 minute)

```bash
pip install -r requirements.txt
```

## Step 4: Run TuneGenie (Done!)

```bash
streamlit run app.py
```

## ✅ Verification

Test that APIs are working:

```bash
python3 test_apis.py
```

You should see:
```
✓ Groq: Working
✓ Gemini: Working
✓ OpenRouter: Working
Total Cost: $0.00
```

## 🎯 Quick Reference

### Minimum Setup (1 API):
- **Groq** = Fast responses
- **OR Gemini** = Best quality
- **OR OpenRouter** = Most flexible

### Recommended Setup (2 APIs):
- **Groq** (primary) + **Gemini** (backup)
- = Fast + Reliable + High Quality

### Maximum Setup (5 APIs):
- **All providers** = Maximum reliability + capacity

## 🔒 Security Notes

1. **Never commit .env to git** (already in .gitignore)
2. **Keep API keys secret** (don't share)
3. **All providers are FREE** (no credit card needed)
4. **Zero cost guaranteed** (see ZERO_COST_GUARANTEE.md)

## 🆘 Troubleshooting

### "No API keys found"
- Check `.env` file exists
- Verify keys are not empty
- Ensure no extra spaces around keys

### "API quota exceeded"
- Check usage dashboard in app
- Wait for quota to reset (1 minute or 1 day)
- Use different provider (automatic fallback)

### "Import errors"
- Run: `pip install -r requirements.txt`
- Verify Python 3.8+ installed

### "Streamlit not found"
- Run: `pip install streamlit`
- Or: `pip install -r requirements.txt`

## 📊 Usage Limits

With **1 API** (Groq):
- ~400 requests/day
- Perfect for personal use

With **2 APIs** (Groq + Gemini):
- ~900 requests/day
- Great for regular use

With **5 APIs** (All):
- ~1,500+ requests/day
- Excellent for heavy use

**All at $0.00 cost!** 🎉

## 🎵 Ready to Rock!

You're all set! TuneGenie will:
- ✅ Connect to Spotify
- ✅ Analyze your music taste
- ✅ Give AI-powered recommendations
- ✅ Create playlists automatically
- ✅ Cost you $0.00 forever

Enjoy! 🎶
