# 📅 Upload Scheduler Guide - TikTok & YouTube Shorts

Complete guide for scheduling your golf videos to TikTok and YouTube Shorts using browser automation.

---

## 🎯 What These Scripts Do

The upload schedulers automate the tedious process of:
1. Opening each video file
2. Adding captions and hashtags
3. Setting the schedule date/time
4. Publishing/scheduling the post

You'll watch it work in a browser window, with prompts when manual input is needed.

---

## 📋 Prerequisites

Before running the schedulers:

✅ **Caption CSV generated** - You should have `golf_captions_schedule.csv`  
✅ **Videos in one folder** - All your golf videos ready to upload  
✅ **Accounts ready** - Logged into TikTok and/or YouTube  
✅ **Playwright installed** - The scripts will install it automatically  

---

## 🚀 Setup Instructions

### Step 1: Install Playwright

The first time you run either scheduler, it will automatically install Playwright and the Chrome browser.

This takes about 2-3 minutes and only happens once.

Alternatively, you can install it manually:

```bash
pip3 install playwright
playwright install chromium
```

---

## 🎬 TikTok Scheduler

### How to Run:

**Option 1: With video folder as argument**
```bash
python3 tiktok_scheduler.py /path/to/your/videos/folder
```

**Option 2: Interactive (it will ask for paths)**
```bash
python3 tiktok_scheduler.py
```

### What Happens:

1. **Script starts** - Verifies your CSV and video files
2. **Browser opens** - Chrome window appears and goes to TikTok
3. **You log in** - Manually log into your TikTok account
4. **Automation begins** - Script uploads each video one by one
5. **Manual confirmations** - You'll confirm schedule times and publish
6. **Completion** - All videos scheduled!

### Important Notes:

- **Keep the browser window open** - Don't close it during automation
- **Manual steps required** - TikTok's interface varies, so you'll confirm some steps
- **One at a time** - Uploads happen sequentially (not in parallel)
- **Takes time** - Expect 2-3 minutes per video (upload + processing)
- **Stay nearby** - You'll need to confirm dates/times and final publish

### TikTok-Specific Tips:

✅ Make sure you're logged into the **right account**  
✅ Complete any **2FA verification** before starting  
✅ TikTok's schedule picker varies by region - **manually set dates/times**  
✅ The script will **pause and wait** for you when needed  
✅ You can **stop anytime** with Control + C  

---

## 📺 YouTube Shorts Scheduler

### How to Run:

**Option 1: With video folder as argument**
```bash
python3 youtube_scheduler.py /path/to/your/videos/folder
```

**Option 2: Interactive (it will ask for paths)**
```bash
python3 youtube_scheduler.py
```

### What Happens:

1. **Script starts** - Verifies your CSV and video files
2. **Browser opens** - Chrome window appears and goes to YouTube Studio
3. **You log in** - Manually log into your YouTube/Google account
4. **Automation begins** - Script uploads each video through YouTube Studio
5. **Manual confirmations** - You'll set "Not made for kids" and confirm schedule
6. **Completion** - All shorts scheduled!

### Important Notes:

- **YouTube Studio** - Uses the full creator studio interface
- **Manual steps required** - More manual than TikTok due to YouTube's complexity
- **Longer uploads** - YouTube processing takes longer (3-5 min per video)
- **Stay logged in** - Don't log out during the process
- **Channel selection** - Make sure you're on the right channel if you have multiple

### YouTube-Specific Tips:

✅ Log into **YouTube Studio** before starting  
✅ Select the **correct channel** (if you manage multiple)  
✅ Videos under **60 seconds** automatically become Shorts  
✅ **"Not made for kids"** selection is required - script will prompt you  
✅ Set visibility to **"Schedule"** not "Public" or "Private"  
✅ Hashtags go in the **description** field  

---

## ⚙️ How The Automation Works

### Semi-Automated Process:

Both scripts use a **hybrid approach**:

**Automated:**
- Opening upload pages
- Selecting video files
- Filling in captions/titles
- Adding hashtags
- Navigating through steps

**Manual (with prompts):**
- Logging in
- Setting exact schedule dates/times
- Confirming "Not made for kids" (YouTube)
- Final publish/schedule confirmation

This approach is **more reliable** because:
- Platform interfaces change frequently
- Date/time pickers vary by region
- Prevents accidental posts
- You maintain control

---

## 📊 Expected Timeline

### For 3 Test Videos:

**TikTok:**
- Setup: 2 minutes
- Per video: 2-3 minutes
- **Total: ~10-12 minutes**

**YouTube:**
- Setup: 2 minutes
- Per video: 3-5 minutes
- **Total: ~12-17 minutes**

### For 60 Videos:

**TikTok:**
- **Total: 2-3 hours** (with breaks recommended)

**YouTube:**
- **Total: 3-5 hours** (with breaks recommended)

**Recommendation:** Do these in batches:
- Upload 10-15 at a time
- Take breaks
- Spread over multiple days if needed

---

## 🛠️ Troubleshooting

### "ModuleNotFoundError: No module named 'playwright'"

**Fix:**
```bash
pip3 install playwright
playwright install chromium
```

### Browser doesn't open

**Fix:**
- Make sure Playwright is fully installed
- Try running: `playwright install chromium`
- Check if Chrome is already installed

### Can't find upload button / interface looks different

**Fix:**
- This is normal! Platforms update frequently
- The script will prompt you to do steps manually
- Follow the on-screen instructions
- You can always complete steps yourself

### Video upload fails

**Fix:**
- Check your internet connection
- Verify the video file isn't corrupted
- Make sure the video meets platform requirements:
  - **TikTok**: Max 10 minutes, vertical preferred
  - **YouTube**: Max 60 seconds for Shorts, vertical 9:16

### Script gets stuck

**Fix:**
- Press **Control + C** to stop
- Close the browser
- Restart the script
- The CSV tracks what's done, so you can resume

### Schedule dates are wrong

**Fix:**
- The CSV has all the correct dates
- You manually confirm each date during upload
- Double-check as you go

---

## 💡 Best Practices

### Before You Start:

✅ **Test with 2-3 videos first** - Make sure it works before doing all 60  
✅ **Check your CSV** - Review captions one more time  
✅ **Stable internet** - Don't run on spotty WiFi  
✅ **Charged laptop** - Don't let it sleep mid-upload  
✅ **Clear schedule** - Set aside uninterrupted time  

### During Upload:

✅ **Stay nearby** - You'll need to confirm steps  
✅ **Don't close browser** - Let it stay open  
✅ **Follow prompts** - Read what the script asks  
✅ **Take breaks** - After every 10-15 videos  
✅ **Verify as you go** - Check each scheduled post  

### After Upload:

✅ **Verify in platform** - Check TikTok/YouTube to see scheduled posts  
✅ **Note any issues** - Track what worked/didn't  
✅ **Keep CSV** - Save it as a record  
✅ **Test posts** - Make sure first few go live correctly  

---

## 🎯 Platform-Specific Requirements

### TikTok:

| Requirement | Details |
|------------|---------|
| **Max Length** | 10 minutes |
| **Aspect Ratio** | 9:16 (vertical) preferred |
| **File Size** | Max 287.6 MB |
| **Formats** | .mp4, .mov, .webm |
| **Schedule** | Up to 10 days in advance |

### YouTube Shorts:

| Requirement | Details |
|------------|---------|
| **Max Length** | 60 seconds (for Shorts) |
| **Aspect Ratio** | 9:16 (vertical) |
| **File Size** | Max 256 GB (but Shorts should be small) |
| **Formats** | .mp4, .mov, .avi, .wmv |
| **Schedule** | Up to 2 weeks in advance |

---

## 🔄 Running the Automation Again

When you want to post your next batch of 60 videos:

1. **Generate new captions** with the caption generator
2. **Review the new CSV**
3. **Run the schedulers again** with the new CSV
4. **Repeat the process**

The scripts are reusable - just point them to your new CSV and videos folder!

---

## ❓ FAQ

**Q: Can I schedule posts months in advance?**  
A: No. TikTok: 10 days max. YouTube: 2 weeks max. Plan accordingly!

**Q: What if I want to cancel a scheduled post?**  
A: Go to your platform and manually unschedule it from your drafts/scheduled posts.

**Q: Can I run both schedulers at the same time?**  
A: No, run them separately. Do TikTok first, then YouTube.

**Q: Do I need to stay logged in after scheduling?**  
A: No, once scheduled, you can log out. Posts will go live automatically.

**Q: What if my video gets rejected/flagged?**  
A: You'll need to manually review and reupload. The platforms will notify you.

**Q: Can I edit scheduled posts later?**  
A: Yes! Go to your scheduled posts in each platform and edit as needed.

---

## 🎉 You're Ready!

You now have:
- ✅ Caption generator (generates captions)
- ✅ TikTok scheduler (uploads to TikTok)
- ✅ YouTube scheduler (uploads to YouTube)

**Workflow:**
1. Generate captions → Review CSV
2. Run TikTok scheduler → Verify scheduled posts
3. Run YouTube scheduler → Verify scheduled posts
4. Wait for posts to go live!
5. Repeat in 60 days with new videos!

---

**Questions?** Test with your 3 videos first and let me know how it goes! 🚀

Made with ⛳ for golf content creators
