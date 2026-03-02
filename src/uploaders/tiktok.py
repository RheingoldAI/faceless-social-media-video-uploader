#!/usr/bin/env python3
"""
TikTok Upload Scheduler
Launches Chrome with a persistent profile and automates TikTok Studio uploads.
Dates are calculated dynamically at runtime from config/posting_schedule.json.

Requirements:
  - Google Chrome installed
  - pip install playwright && playwright install chromium
  - First run: log into TikTok when Chrome opens (session is saved)
"""

import os
import sys
import csv
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
import subprocess

# Resolve project root (parent of src/uploaders/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Installing Playwright...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    from playwright.sync_api import sync_playwright


def load_posting_schedule():
    """Load day-of-week posting times from config."""
    schedule_path = PROJECT_ROOT / 'config' / 'posting_schedule.json'
    with open(schedule_path, 'r') as f:
        return json.load(f)


def calculate_post_dates(num_videos, schedule, start_date=None):
    """Calculate posting dates for N videos starting from tomorrow."""
    if start_date is None:
        start_date = datetime.now().date() + timedelta(days=1)

    dates = []
    current_date = start_date

    while len(dates) < num_videos:
        weekday_name = current_date.strftime('%A')
        if weekday_name in schedule:
            dates.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'weekday': weekday_name,
                'tiktok_time': schedule[weekday_name]['tiktok'],
                'youtube_time': schedule[weekday_name]['youtube'],
            })
        current_date += timedelta(days=1)

    return dates


def round_to_5_minutes(time_str):
    """Round a HH:MM time string to the nearest 5-minute increment.
    TikTok's time picker only supports 5-minute steps."""
    hours, minutes = map(int, time_str.split(':'))
    rounded_minutes = round(minutes / 5) * 5
    if rounded_minutes == 60:
        rounded_minutes = 0
        hours = (hours + 1) % 24
    return f"{hours:02d}:{rounded_minutes:02d}"


class TikTokScheduler:
    def __init__(self, csv_path, videos_folder):
        self.csv_path = Path(csv_path)
        self.videos_folder = Path(videos_folder)
        self.scheduled_count = 0
        self.skipped = []  # Track skipped/failed videos with reasons
        self.schedule = load_posting_schedule()

    def read_csv(self):
        """Read the captions CSV file"""
        videos = []
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                videos.append(row)
        return videos

    def dismiss_modals(self, page):
        """Dismiss any TikTok popups/modals that may appear during the flow.
        Handles the 'Continue to post?' check modal and other common dialogs.
        Safe to call at any time — does nothing if no modals are present."""
        try:
            dismissed = page.evaluate("""
                () => {
                    const dismissed = [];

                    // Known button labels we always want to click
                    const clickLabels = ['Post now', 'Got it', 'OK', 'Dismiss', 'Continue'];
                    const buttons = [...document.querySelectorAll('button')];

                    for (const btn of buttons) {
                        const text = btn.textContent.trim();
                        if (clickLabels.includes(text) && btn.offsetParent !== null) {
                            btn.click();
                            dismissed.push(text);
                            break;  // one modal at a time
                        }
                    }

                    // Also try closing any generic dialog close buttons (X icons)
                    if (dismissed.length === 0) {
                        const closeSelectors = [
                            '[aria-label="Close"]', '[aria-label="close"]',
                            'button[class*="close" i]', 'button[class*="Close"]',
                            '[data-e2e="modal-close-btn"]',
                        ];
                        for (const sel of closeSelectors) {
                            const el = document.querySelector(sel);
                            if (el && el.offsetParent !== null) {
                                el.click();
                                dismissed.push('close-btn');
                                break;
                            }
                        }
                    }

                    return dismissed;
                }
            """)
            if dismissed:
                print(f"   → Dismissed modal: {dismissed}")
                time.sleep(1)
            return dismissed
        except:
            return []

    def upload_file(self, page, video_path):
        """Upload a file using Playwright's set_input_files.
        Works for all file sizes when Chrome is launched locally."""
        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        print(f"   → File size: {file_size_mb:.1f} MB")
        try:
            file_input = page.locator('input[type="file"]').first
            file_input.set_input_files(str(video_path))
            print(f"   ✓ File selected")
            return True
        except Exception as e:
            print(f"   ❌ File upload failed: {e}")
            return False

    def wait_for_editing_view(self, page, timeout=60):
        """Wait for the TikTok editing view to load after file upload.
        Polls for the 'When to post' text or caption field to appear."""
        print("   → Waiting for editing view to load...")
        start = time.time()
        while time.time() - start < timeout:
            try:
                ready = page.evaluate("""
                    () => {
                        // Check for "When to post" text (Settings section)
                        const allText = document.body.innerText || '';
                        if (allText.includes('When to post')) return 'settings';
                        // Check for contenteditable caption field
                        const ce = document.querySelector('[contenteditable="true"]');
                        if (ce && ce.offsetParent !== null) return 'caption';
                        // Check for the schedule container
                        const sc = document.querySelector('[data-e2e="schedule_container"]');
                        if (sc) return 'schedule';
                        return null;
                    }
                """)
                if ready:
                    print(f"   ✓ Editing view ready (detected: {ready})")
                    return True
            except:
                pass
            time.sleep(2)
        print(f"   ❌ Editing view did not load within {timeout}s")
        return False

    def click_schedule_radio(self, page):
        """Activate the Schedule radio button using JavaScript click."""
        result = page.evaluate("""
            () => {
                const allElements = [...document.querySelectorAll('span')];
                for (const el of allElements) {
                    const directText = Array.from(el.childNodes)
                        .filter(n => n.nodeType === 3)
                        .map(n => n.textContent.trim())
                        .join('');
                    if (directText === 'Schedule') {
                        // Click the span and its parent label
                        el.click();
                        if (el.parentElement && el.parentElement.tagName === 'LABEL') {
                            el.parentElement.click();
                        }
                        return { clicked: true };
                    }
                }
                return { clicked: false };
            }
        """)
        return result.get('clicked', False)

    def set_date(self, page, date_str):
        """Set the schedule date via the calendar picker popup.
        Clicks the date input to open the calendar, navigates to the
        correct month with the arrow buttons, then clicks the target day."""
        target_year = int(date_str[:4])
        target_month = int(date_str[5:7])
        target_day = int(date_str[8:10])

        MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']

        # Step 1: Click the date input to open the calendar
        date_input = None
        for inp in page.locator('input.TUXTextInputCore-input').all():
            try:
                value = inp.input_value()
                if len(value) == 10 and value[4] == '-' and value[7] == '-':
                    date_input = inp
                    inp.click()
                    time.sleep(1)
                    break
            except:
                continue

        if not date_input:
            print(f"   ❌ Could not find date input")
            return False

        # Step 2: Verify calendar opened and read current month/year
        cal = page.locator('[class*="calendar-wrapper"]')
        if not cal.is_visible(timeout=3000):
            print(f"   ❌ Calendar did not open")
            return False

        cal_text = cal.text_content()[:50]
        current_month = None
        for i, name in enumerate(MONTH_NAMES):
            if name in cal_text:
                current_month = i + 1
                break

        current_year = None
        for j in range(len(cal_text) - 3):
            chunk = cal_text[j:j + 4]
            if chunk.isdigit():
                current_year = int(chunk)
                break

        if not current_month or not current_year:
            print(f"   ❌ Could not parse calendar: '{cal_text}'")
            return False

        print(f"   → Calendar: {MONTH_NAMES[current_month - 1]} {current_year}")

        # Step 3: Navigate to the target month
        months_diff = (target_year - current_year) * 12 + (target_month - current_month)
        if months_diff != 0:
            cal_arrows = cal.locator('span[class*="arrow"]')
            arrow = cal_arrows.last if months_diff > 0 else cal_arrows.first
            for _ in range(abs(months_diff)):
                arrow.click()
                time.sleep(0.5)
            direction = "forward" if months_diff > 0 else "back"
            print(f"   → Navigated {direction} {abs(months_diff)} month(s)")
            time.sleep(0.3)

        # Step 4: Click the target day cell
        day_clicked = False
        day_cells = cal.locator('span[class*="day"][class*="valid"]').all()
        if not day_cells:
            day_cells = cal.locator('span[class*="day"]').all()

        for cell in day_cells:
            try:
                if cell.text_content().strip() == str(target_day):
                    cell.click()
                    day_clicked = True
                    time.sleep(0.5)
                    break
            except:
                continue

        if not day_clicked:
            print(f"   ❌ Day {target_day} not found/clickable in calendar")
            return False

        # Verify
        new_val = date_input.input_value()
        if new_val == date_str:
            print(f"   ✓ Date set: {date_str}")
        else:
            print(f"   ⚠️  Date input shows '{new_val}' (expected {date_str})")
        return True

    def set_time(self, page, time_str):
        """Set the time via TikTok's scroll picker. Falls back to fill()/keyboard."""
        rounded_time = round_to_5_minutes(time_str)
        if rounded_time != time_str:
            print(f"   → Time rounded to 5-min increment: {time_str} → {rounded_time}")

        target_hour = rounded_time.split(':')[0]
        target_minute = rounded_time.split(':')[1]

        # Step 1: Find and click the time input to open the picker dropdown
        time_input = None
        all_inputs = page.locator('input.TUXTextInputCore-input').all()
        for inp in all_inputs:
            try:
                value = inp.input_value()
                if len(value) == 5 and value[2] == ':' and value.replace(':', '').isdigit():
                    time_input = inp
                    inp.click()
                    time.sleep(1)
                    break
            except:
                continue

        if not time_input:
            print(f"   ❌ Could not find time input")
            return False

        # Step 2: Ensure picker is visible (remove TikTok's invisible class)
        page.evaluate("""
            () => {
                const c = document.querySelector('.tiktok-timepicker-time-picker-container');
                if (c) c.classList.remove('tiktok-timepicker-invisible');
            }
        """)
        time.sleep(0.5)

        # Step 3: Click hour/minute items using Playwright (fires trusted events)
        hour_set = False
        minute_set = False

        try:
            hour_items = page.locator('.tiktok-timepicker-option-text.tiktok-timepicker-left').all()
            for item in hour_items:
                try:
                    if item.text_content().strip() == target_hour:
                        item.scroll_into_view_if_needed()
                        time.sleep(0.2)
                        item.click()
                        hour_set = True
                        time.sleep(0.3)
                        break
                except:
                    continue
        except:
            pass

        try:
            minute_items = page.locator('.tiktok-timepicker-option-text.tiktok-timepicker-right').all()
            for item in minute_items:
                try:
                    if item.text_content().strip() == target_minute:
                        item.scroll_into_view_if_needed()
                        time.sleep(0.2)
                        item.click()
                        minute_set = True
                        time.sleep(0.3)
                        break
                except:
                    continue
        except:
            pass

        if hour_set and minute_set:
            print(f"   ✓ Time set to: {rounded_time} (via picker)")
            page.keyboard.press("Escape")
            time.sleep(0.3)
            return True

        # Fallback: Playwright fill() on the time input
        missing = []
        if not hour_set:
            missing.append('hour')
        if not minute_set:
            missing.append('minute')
        print(f"   → Picker {'+'.join(missing)} not found, trying fill/keyboard...")

        try:
            time_input.fill(rounded_time)
            time.sleep(0.5)
            new_val = time_input.input_value()
            if new_val == rounded_time:
                print(f"   ✓ Time set to: {rounded_time} (via fill)")
                page.keyboard.press("Escape")
                time.sleep(0.3)
                return True
            print(f"   → fill() shows '{new_val}', trying keyboard...")
        except Exception:
            pass

        # Last resort: select-all + type
        try:
            time_input.click()
            time.sleep(0.2)
            page.keyboard.press("Meta+a")
            time.sleep(0.1)
            page.keyboard.type(rounded_time, delay=30)
            time.sleep(0.3)
            page.keyboard.press("Enter")
            time.sleep(0.5)
            print(f"   → Time typed via keyboard: {rounded_time}")
            return True
        except Exception:
            pass

        print(f"   ❌ Could not set time")
        return False

    def upload_to_tiktok(self, page, video_info, video_path, post_date, post_time):
        """Upload and schedule a single video to TikTok.

        Returns True on success, False on failure. Never raises — all errors
        are caught, logged, and added to self.skipped so the batch continues.
        """
        filename = video_info['filename']

        try:
            print(f"\n📤 Uploading: {filename}")
            print(f"   Caption: {video_info['tiktok_caption'][:50]}...")
            print(f"   Schedule: {post_date} at {post_time}")

            # Navigate to upload page
            print("   → Going to upload page...")
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    page.goto("https://www.tiktok.com/tiktokstudio/upload",
                              wait_until="domcontentloaded", timeout=30000)
                    print("   ✓ Upload page loaded")
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"   ⚠️  Navigation attempt {attempt + 1} failed, retrying...")
                        time.sleep(2)
                    else:
                        raise e

            time.sleep(4)

            # Upload file via CDP (handles files >50MB)
            print("   → Selecting video file...")
            if not self.upload_file(page, video_path):
                self.skipped.append({'filename': filename, 'reason': 'File upload failed'})
                return False

            # Wait for the editing view to load (polls instead of fixed sleep)
            if not self.wait_for_editing_view(page, timeout=60):
                self.skipped.append({'filename': filename, 'reason': 'Editing view never loaded after upload'})
                return False

            # Extra settle time for all elements to render
            time.sleep(3)

            # Dismiss any popups/modals that appeared
            self.dismiss_modals(page)

            # Add caption
            caption_text = f"{video_info['tiktok_caption']} {video_info['tiktok_hashtags']}"
            print(f"   → Adding caption...")

            caption_selectors = [
                'div[contenteditable="true"][data-text="true"]',
                'div[contenteditable="true"]',
                'div.DraftEditor-editorContainer div[contenteditable="true"]',
                '[data-contents="true"]',
                'div[role="textbox"]'
            ]

            caption_added = False
            for selector in caption_selectors:
                try:
                    caption_field = page.locator(selector).first
                    if caption_field.is_visible(timeout=3000):
                        caption_field.click()
                        time.sleep(0.5)
                        page.keyboard.press("Meta+a")
                        time.sleep(0.2)
                        page.keyboard.press("Backspace")
                        time.sleep(0.3)
                        caption_field.type(caption_text, delay=30)
                        caption_added = True
                        print("   ✓ Caption added!")
                        break
                except:
                    continue

            if not caption_added:
                print(f"   ⚠️  Could not auto-fill caption (will continue without)")
                self.skipped.append({'filename': filename, 'reason': 'Caption auto-fill failed (video still uploaded)'})

            time.sleep(1)

            # Dismiss hashtag suggestions
            try:
                page.keyboard.press("Escape")
                time.sleep(0.5)
            except:
                pass

            # Click Schedule radio (retry a few times as page may still be settling)
            print(f"   → Activating Schedule mode...")
            schedule_activated = False
            for attempt in range(5):
                if self.click_schedule_radio(page):
                    time.sleep(2)
                    # Verify it actually activated by checking for date/time inputs
                    has_picker = page.evaluate("""
                        () => {
                            const inputs = document.querySelectorAll('input.TUXTextInputCore-input');
                            for (const inp of inputs) {
                                if (inp.value && inp.value.includes('-') && inp.value.length === 10)
                                    return true;
                            }
                            return false;
                        }
                    """)
                    if has_picker:
                        schedule_activated = True
                        break
                    else:
                        print(f"   → Schedule clicked but picker not visible yet, retrying ({attempt + 1}/5)...")
                else:
                    print(f"   → Schedule radio not found yet, retrying ({attempt + 1}/5)...")
                time.sleep(2)

            if not schedule_activated:
                reason = "Could not activate Schedule mode after 5 attempts"
                print(f"   ❌ {reason}")
                self.skipped.append({'filename': filename, 'reason': reason})
                return False

            print("   ✓ Schedule mode activated!")

            # Set date
            print(f"   → Setting date to {post_date}...")
            if not self.set_date(page, post_date):
                reason = "Could not set schedule date"
                print(f"   ❌ {reason}")
                self.skipped.append({'filename': filename, 'reason': reason})
                return False

            # Set time
            print(f"   → Setting time to {post_time}...")
            if not self.set_time(page, post_time):
                reason = "Could not set schedule time"
                print(f"   ❌ {reason}")
                self.skipped.append({'filename': filename, 'reason': reason})
                return False

            time.sleep(1)

            # Verify date/time values before submitting
            actual_values = page.evaluate("""
                () => {
                    const inputs = document.querySelectorAll('input.TUXTextInputCore-input');
                    let date = null, time = null;
                    for (const inp of inputs) {
                        const v = inp.value || '';
                        if (v.length === 10 && v[4] === '-' && v[7] === '-') date = v;
                        if (v.length === 5 && v[2] === ':') time = v;
                    }
                    return { date, time };
                }
            """)
            print(f"   📋 Pre-submit check — date: {actual_values.get('date')}, time: {actual_values.get('time')}")
            if actual_values.get('date') != post_date:
                print(f"   ⚠️  Date mismatch! Expected {post_date}, got {actual_values.get('date')}")
            if actual_values.get('time') != round_to_5_minutes(post_time):
                print(f"   ⚠️  Time mismatch! Expected {round_to_5_minutes(post_time)}, got {actual_values.get('time')}")

            # Click the Schedule submit button
            print("   → Clicking Schedule button...")
            schedule_btn = None

            # The submit button has text "Schedule" and is a primary button
            try:
                buttons = page.locator('button').all()
                for btn in buttons:
                    try:
                        text = btn.text_content().strip()
                        classes = btn.get_attribute('class') or ''
                        if text == 'Schedule' and 'primary' in classes.lower():
                            schedule_btn = btn
                            break
                    except:
                        continue
            except:
                pass

            if not schedule_btn:
                # Fallback: find by data-e2e or button text
                try:
                    schedule_btn = page.locator('button:has-text("Schedule")').last
                except:
                    pass

            if schedule_btn:
                schedule_btn.click()
                print("   ✓ Schedule button clicked!")
                time.sleep(3)
                # Handle "Continue to post?" modal (video check still running)
                self.dismiss_modals(page)
                time.sleep(2)
            else:
                reason = "Could not find Schedule submit button"
                print(f"   ❌ {reason}")
                self.skipped.append({'filename': filename, 'reason': reason})
                return False

            print(f"   ✅ Scheduled: {filename} → {post_date} at {post_time}")
            return True

        except Exception as e:
            reason = f"Unexpected error: {e}"
            print(f"   ❌ {reason}")
            self.skipped.append({'filename': filename, 'reason': reason})
            return False

    def run(self):
        """Main execution"""
        print("🎬 TikTok Upload Scheduler")
        print("=" * 60)

        # Read CSV
        print(f"\n📄 CSV: {self.csv_path}")
        videos = self.read_csv()
        print(f"✓ Found {len(videos)} videos")

        # Calculate posting dates dynamically
        post_dates = calculate_post_dates(len(videos), self.schedule)

        print(f"\n📅 Schedule preview:")
        print(f"   Starts: {post_dates[0]['date']} ({post_dates[0]['weekday']})")
        print(f"   Ends:   {post_dates[-1]['date']} ({post_dates[-1]['weekday']})")

        # Check files
        print(f"\n📁 Videos: {self.videos_folder}")
        missing = []
        for video in videos:
            if not (self.videos_folder / video['filename']).exists():
                missing.append(video['filename'])

        if missing:
            print("\n⚠️  Missing:")
            for f in missing:
                print(f"   - {f}")
            if input("\nContinue? (yes/no): ").strip().lower() not in ['yes', 'y']:
                return

        # BATCH UPLOAD OPTION
        print("\n" + "=" * 60)
        print("📦 BATCH UPLOAD OPTIONS")
        print("=" * 60)
        print("\nYou can upload in batches to manage large video libraries.\n")

        use_batch = input("Do you want to upload in batches? (yes/no): ").strip().lower()

        if use_batch in ['yes', 'y']:
            batch_size = input("\nHow many videos per batch? (default: 10): ").strip()
            batch_size = int(batch_size) if batch_size.isdigit() else 10

            total_batches = (len(videos) + batch_size - 1) // batch_size

            print(f"\n📊 Upload Plan:")
            print(f"   Total videos: {len(videos)}")
            print(f"   Batch size: {batch_size}")
            print(f"   Total batches: {total_batches}")

            for i in range(total_batches):
                start_idx = i * batch_size
                end_idx = min(start_idx + batch_size, len(videos))
                first_date = post_dates[start_idx]
                last_date = post_dates[end_idx - 1]
                print(f"   Batch {i+1}: Videos {start_idx+1}-{end_idx} ({first_date['date']} → {last_date['date']})")

            print(f"\n" + "=" * 60)
            batch_num = input(f"Which batch do you want to upload now? (1-{total_batches}): ").strip()

            if not batch_num.isdigit() or int(batch_num) < 1 or int(batch_num) > total_batches:
                print("❌ Invalid batch number. Cancelled.")
                return

            batch_num = int(batch_num)
            start_idx = (batch_num - 1) * batch_size
            end_idx = min(start_idx + batch_size, len(videos))

            videos_to_upload = videos[start_idx:end_idx]
            dates_to_use = post_dates[start_idx:end_idx]

            print(f"\n✓ Selected Batch {batch_num}")
            print(f"✓ Uploading videos {start_idx+1} to {end_idx}")
            print(f"✓ Scheduling: {dates_to_use[0]['date']} → {dates_to_use[-1]['date']}")
            print(f"✓ Total: {len(videos_to_upload)} videos\n")
        else:
            videos_to_upload = videos
            dates_to_use = post_dates
            batch_num = 1
            total_batches = 1
            print("\n✓ Uploading all videos\n")

        profile_dir = str(Path.home() / '.chrome-debug-profile')

        print("\n🌐 Launching Chrome...")
        print("   (TikTok login is saved in the debug profile)")

        with sync_playwright() as p:
            try:
                context = p.chromium.launch_persistent_context(
                    profile_dir,
                    headless=False,
                    channel='chrome',
                    args=['--disable-blink-features=AutomationControlled'],
                )
                page = context.pages[0] if context.pages else context.new_page()
                print("   ✓ Chrome launched!")
            except Exception as e:
                print(f"\n❌ Could not launch Chrome!")
                print(f"   Error: {e}")
                print("\n📖 Troubleshooting:")
                print("   • Close any Chrome windows that use the debug profile")
                print("   • Make sure Google Chrome is installed")
                print("   • Run:  playwright install chromium  (if Chrome channel fails)")
                return

            # Verify TikTok access
            print("\n👉 Make sure you're logged into TikTok in this Chrome window")
            print("   (First time? Log in now — your session will be saved)")
            input("   Press ENTER when ready...")

            # Process videos
            for idx, (video_info, date_info) in enumerate(zip(videos_to_upload, dates_to_use), 1):
                print(f"\n{'=' * 60}")
                print(f"Video {idx}/{len(videos_to_upload)}")
                print(f"{'=' * 60}")

                video_path = self.videos_folder / video_info['filename']

                if not video_path.exists():
                    print(f"⚠️  Skipping {video_info['filename']} — file not found")
                    self.skipped.append({'filename': video_info['filename'], 'reason': 'File not found'})
                    continue

                if self.upload_to_tiktok(page, video_info, video_path,
                                         date_info['date'], date_info['tiktok_time']):
                    self.scheduled_count += 1

                # Always continue to next video regardless of success/failure

                if idx < len(videos_to_upload):
                    print("\n⏳ Waiting 5 seconds before next upload...")
                    time.sleep(5)

            # ── Final Summary ──
            print("\n" + "=" * 60)
            print("🎉 COMPLETE!")
            print("=" * 60)
            print(f"\n✅ Scheduled: {self.scheduled_count}/{len(videos_to_upload)} videos")

            if self.skipped:
                print(f"\n⚠️  Issues ({len(self.skipped)} videos):")
                for item in self.skipped:
                    print(f"   • {item['filename']}")
                    print(f"     └─ {item['reason']}")

            if use_batch in ['yes', 'y'] and batch_num < total_batches:
                print(f"\n💡 TIP: To upload the next batch, run this script again")
                print(f"    and select Batch {batch_num + 1}")

            input("\nPress ENTER to close Chrome and finish...")


def main():
    print("🎬 TikTok Upload Scheduler")
    print("=" * 60)

    csv_path = str(PROJECT_ROOT / "data" / "golf_captions.csv")
    if not os.path.exists(csv_path):
        csv_path = input("\nCSV path: ").strip()
        if not os.path.exists(csv_path):
            print(f"❌ Not found: {csv_path}")
            sys.exit(1)

    print(f"\n✓ CSV: {csv_path}")

    if len(sys.argv) > 1:
        videos_folder = sys.argv[1]
    else:
        videos_folder = str(PROJECT_ROOT / "videos")

    if not os.path.exists(videos_folder):
        print(f"❌ Not found: {videos_folder}")
        sys.exit(1)

    print(f"✓ Videos: {videos_folder}")

    print("\n" + "=" * 60)
    print("This script will launch Chrome automatically.")
    print("Your TikTok login is saved between sessions.")
    print("(First time? You'll need to log into TikTok when Chrome opens)")
    print("=" * 60)

    response = input("\nReady to start? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("\nOK, come back when you're ready!")
        sys.exit(0)

    scheduler = TikTokScheduler(csv_path, videos_folder)
    scheduler.run()


if __name__ == "__main__":
    main()
