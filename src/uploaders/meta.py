#!/usr/bin/env python3
"""
Meta (Instagram + Facebook) Reels Upload Scheduler
Automates uploading and scheduling Reels to Instagram and Facebook Pages
using the Meta Graph API.

Dates are calculated dynamically at runtime from config/posting_schedule.json.

Setup required:
  1. Create a Meta Developer App at https://developers.facebook.com/apps/
  2. Add Instagram Graph API and Facebook Login products
  3. Generate a never-expiring Page Access Token (see docs/SETUP.md)
  4. Create config/meta_config.json with your credentials
  5. pip install requests
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
    import requests
except ImportError:
    print("Installing requests...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

API_VERSION = 'v21.0'
GRAPH_URL = f'https://graph.facebook.com/{API_VERSION}'


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
                'meta_time': schedule[weekday_name].get('meta', schedule[weekday_name].get('youtube', '12:00')),
                'tiktok_time': schedule[weekday_name]['tiktok'],
                'youtube_time': schedule[weekday_name]['youtube'],
            })
        current_date += timedelta(days=1)

    return dates


class MetaUploader:
    def __init__(self, csv_path, videos_folder):
        self.csv_path = Path(csv_path)
        self.videos_folder = Path(videos_folder)
        self.uploaded_count = 0
        self.skipped = []
        self.schedule = load_posting_schedule()
        self.config = None

    def load_config(self):
        """Load Meta API credentials from config file."""
        config_path = PROJECT_ROOT / 'config' / 'meta_config.json'
        if not config_path.exists():
            print(f"\n❌ Config file not found: {config_path}")
            print("\nCreate config/meta_config.json with:")
            print(json.dumps({
                "page_access_token": "YOUR_NEVER_EXPIRING_PAGE_ACCESS_TOKEN",
                "page_id": "YOUR_FACEBOOK_PAGE_ID",
                "ig_user_id": "YOUR_INSTAGRAM_BUSINESS_ACCOUNT_ID"
            }, indent=2))
            print("\nSee docs/SETUP.md for instructions.")
            return False

        with open(config_path, 'r') as f:
            self.config = json.load(f)

        required = ['page_access_token', 'page_id', 'ig_user_id']
        missing = [k for k in required if not self.config.get(k)]
        if missing:
            print(f"\n❌ Missing fields in meta_config.json: {', '.join(missing)}")
            return False

        return True

    def validate_token(self):
        """Test the access token with a simple API call."""
        print("\n🔐 Validating Meta API token...")

        try:
            # Test page token
            resp = requests.get(f"{GRAPH_URL}/{self.config['page_id']}",
                                params={'access_token': self.config['page_access_token'],
                                        'fields': 'name,id'})
            if resp.status_code != 200:
                error = resp.json().get('error', {})
                print(f"   ❌ Page token invalid: {error.get('message', resp.text)}")
                return False

            page_name = resp.json().get('name', 'Unknown')
            print(f"   ✓ Facebook Page: {page_name}")

            # Test IG account
            resp = requests.get(f"{GRAPH_URL}/{self.config['ig_user_id']}",
                                params={'access_token': self.config['page_access_token'],
                                        'fields': 'username,id'})
            if resp.status_code != 200:
                error = resp.json().get('error', {})
                print(f"   ❌ Instagram account error: {error.get('message', resp.text)}")
                return False

            ig_name = resp.json().get('username', 'Unknown')
            print(f"   ✓ Instagram: @{ig_name}")
            print("   ✓ Token validated!")
            return True

        except Exception as e:
            print(f"   ❌ Validation error: {e}")
            return False

    def read_csv(self):
        """Read the captions CSV file."""
        videos = []
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                videos.append(row)
        return videos

    # ── Instagram Reels (Resumable Upload) ──────────────────────────

    def upload_instagram_reel(self, video_path, caption, schedule_timestamp=None):
        """Upload a Reel to Instagram using the resumable upload flow.

        1. Create a media container with upload_type=resumable
        2. Upload binary data to rupload endpoint
        3. Poll status until FINISHED
        4. Publish the container

        Returns the media ID on success, None on failure.
        """
        token = self.config['page_access_token']
        ig_user_id = self.config['ig_user_id']

        # Step 1: Create container
        params = {
            'media_type': 'REELS',
            'upload_type': 'resumable',
            'caption': caption,
            'access_token': token,
        }

        if schedule_timestamp:
            params['published'] = 'false'
            params['scheduled_publish_time'] = str(schedule_timestamp)

        resp = requests.post(f"{GRAPH_URL}/{ig_user_id}/media", data=params)

        if resp.status_code != 200:
            error = resp.json().get('error', {})
            print(f"   ❌ IG container creation failed: {error.get('message', resp.text)}")
            return None

        container_id = resp.json().get('id')
        if not container_id:
            print(f"   ❌ No container ID returned: {resp.text}")
            return None

        print(f"   → IG container created: {container_id}")

        # Step 2: Upload binary data
        file_size = video_path.stat().st_size
        upload_url = f"https://rupload.facebook.com/ig-api-upload/{API_VERSION}/{container_id}"

        headers = {
            'Authorization': f'OAuth {token}',
            'offset': '0',
            'file_size': str(file_size),
            'Content-Type': 'application/octet-stream',
        }

        with open(video_path, 'rb') as f:
            upload_resp = requests.post(upload_url, headers=headers, data=f)

        if upload_resp.status_code != 200:
            print(f"   ❌ IG binary upload failed: {upload_resp.text}")
            return None

        print(f"   ✓ IG video uploaded ({file_size / (1024*1024):.1f} MB)")

        # Step 3: Poll status until FINISHED (or timeout)
        print(f"   → Waiting for IG processing...")
        max_wait = 300  # 5 minutes
        start = time.time()
        while time.time() - start < max_wait:
            status_resp = requests.get(
                f"{GRAPH_URL}/{container_id}",
                params={'fields': 'status_code,status', 'access_token': token}
            )
            if status_resp.status_code == 200:
                status_code = status_resp.json().get('status_code', '')
                if status_code == 'FINISHED':
                    print(f"   ✓ IG processing complete")
                    break
                elif status_code == 'ERROR':
                    status_msg = status_resp.json().get('status', '')
                    print(f"   ❌ IG processing error: {status_msg}")
                    return None
                elif status_code == 'EXPIRED':
                    print(f"   ❌ IG container expired")
                    return None
            time.sleep(5)
        else:
            print(f"   ❌ IG processing timed out after {max_wait}s")
            return None

        # Step 4: Publish
        publish_resp = requests.post(
            f"{GRAPH_URL}/{ig_user_id}/media_publish",
            data={'creation_id': container_id, 'access_token': token}
        )

        if publish_resp.status_code != 200:
            error = publish_resp.json().get('error', {})
            print(f"   ❌ IG publish failed: {error.get('message', publish_resp.text)}")
            return None

        media_id = publish_resp.json().get('id')
        print(f"   ✓ IG Reel published! ID: {media_id}")
        return media_id

    # ── Facebook Reels (Binary Upload) ──────────────────────────────

    def upload_facebook_reel(self, video_path, description, schedule_timestamp=None):
        """Upload a Reel to a Facebook Page.

        1. Initialize upload session (upload_phase=start)
        2. Upload binary video data
        3. Finish upload and publish/schedule (upload_phase=finish)

        Returns the video ID on success, None on failure.
        """
        token = self.config['page_access_token']
        page_id = self.config['page_id']

        # Step 1: Initialize upload
        init_resp = requests.post(
            f"{GRAPH_URL}/{page_id}/video_reels",
            data={
                'upload_phase': 'start',
                'access_token': token,
            }
        )

        if init_resp.status_code != 200:
            error = init_resp.json().get('error', {})
            print(f"   ❌ FB init failed: {error.get('message', init_resp.text)}")
            return None

        init_data = init_resp.json()
        video_id = init_data.get('video_id')
        upload_url = init_data.get('upload_url')

        if not video_id:
            print(f"   ❌ No video_id returned: {init_resp.text}")
            return None

        print(f"   → FB upload initialized: {video_id}")

        # Step 2: Upload binary data
        file_size = video_path.stat().st_size
        headers = {
            'Authorization': f'OAuth {token}',
            'offset': '0',
            'file_size': str(file_size),
            'Content-Type': 'application/octet-stream',
        }

        # Use the upload_url from the init response, or construct it
        if not upload_url:
            upload_url = f"https://rupload.facebook.com/video-upload/{API_VERSION}/{video_id}"

        with open(video_path, 'rb') as f:
            upload_resp = requests.post(upload_url, headers=headers, data=f)

        if upload_resp.status_code not in (200, 201):
            print(f"   ❌ FB binary upload failed: {upload_resp.text}")
            return None

        print(f"   ✓ FB video uploaded ({file_size / (1024*1024):.1f} MB)")

        # Step 3: Finish upload and publish/schedule
        finish_params = {
            'upload_phase': 'finish',
            'video_id': video_id,
            'access_token': token,
            'description': description,
        }

        if schedule_timestamp:
            finish_params['video_state'] = 'SCHEDULED'
            finish_params['publish_time'] = str(schedule_timestamp)
        else:
            finish_params['video_state'] = 'PUBLISHED'

        finish_resp = requests.post(
            f"{GRAPH_URL}/{page_id}/video_reels",
            data=finish_params
        )

        if finish_resp.status_code != 200:
            error = finish_resp.json().get('error', {})
            print(f"   ❌ FB publish failed: {error.get('message', finish_resp.text)}")
            return None

        success = finish_resp.json().get('success', False)
        if success:
            print(f"   ✓ FB Reel published! Video ID: {video_id}")
        else:
            print(f"   ⚠️  FB response: {finish_resp.json()}")

        return video_id

    # ── Combined Upload ─────────────────────────────────────────────

    def upload_video(self, video_info, video_path, post_date, post_time):
        """Upload a single video to both Instagram and Facebook.

        Returns True if at least one platform succeeded, False if both failed.
        """
        filename = video_info['filename']

        try:
            # Build caption — use meta-specific if available, fall back to tiktok
            caption_field = 'meta_caption' if 'meta_caption' in video_info and video_info.get('meta_caption') else 'tiktok_caption'
            hashtag_field = 'meta_hashtags' if 'meta_hashtags' in video_info and video_info.get('meta_hashtags') else 'tiktok_hashtags'

            caption = video_info.get(caption_field, '')
            hashtags = video_info.get(hashtag_field, '')
            full_caption = f"{caption} {hashtags}".strip()

            print(f"\n📤 Uploading: {filename}")
            print(f"   Caption: {caption[:50]}...")
            print(f"   Schedule: {post_date} at {post_time}")

            # Calculate Unix timestamp for scheduling
            schedule_dt = datetime.strptime(f"{post_date} {post_time}", "%Y-%m-%d %H:%M")
            schedule_timestamp = int(schedule_dt.timestamp())

            # Check that schedule is in the future
            if schedule_timestamp <= int(time.time()):
                print(f"   ⚠️  Schedule time is in the past, posting immediately")
                schedule_timestamp = None

            ig_success = False
            fb_success = False

            # Upload to Instagram
            print(f"\n   📸 Instagram Reel:")
            try:
                ig_id = self.upload_instagram_reel(video_path, full_caption, schedule_timestamp)
                ig_success = ig_id is not None
            except Exception as e:
                print(f"   ❌ Instagram error: {e}")

            # Upload to Facebook
            print(f"\n   📘 Facebook Reel:")
            try:
                fb_id = self.upload_facebook_reel(video_path, full_caption, schedule_timestamp)
                fb_success = fb_id is not None
            except Exception as e:
                print(f"   ❌ Facebook error: {e}")

            # Log results
            if ig_success and fb_success:
                sched_str = f"{post_date} at {post_time}" if schedule_timestamp else "immediately"
                print(f"\n   ✅ Both platforms: {filename} → {sched_str}")
                return True
            elif ig_success or fb_success:
                failed = "Facebook" if ig_success else "Instagram"
                print(f"\n   ⚠️  Partial: {filename} ({failed} failed)")
                self.skipped.append({
                    'filename': filename,
                    'reason': f'{failed} upload failed (other platform succeeded)'
                })
                return True
            else:
                reason = "Both Instagram and Facebook uploads failed"
                print(f"\n   ❌ {reason}")
                self.skipped.append({'filename': filename, 'reason': reason})
                return False

        except Exception as e:
            reason = f"Unexpected error: {e}"
            print(f"   ❌ {reason}")
            self.skipped.append({'filename': filename, 'reason': reason})
            return False

    def run(self):
        """Main execution."""
        print("📸 Meta (Instagram + Facebook) Reels Upload Scheduler")
        print("=" * 60)

        # Load config
        if not self.load_config():
            return

        # Validate token
        if not self.validate_token():
            print("\n❌ Token validation failed. Check config/meta_config.json")
            return

        # Read CSV
        print(f"\n📄 CSV: {self.csv_path}")
        videos = self.read_csv()
        print(f"✓ Found {len(videos)} videos")

        # Calculate posting dates
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
            print(f"\n⚠️  Missing {len(missing)} videos:")
            for f in missing:
                print(f"   - {f}")
            if input("\nContinue? (yes/no): ").strip().lower() not in ['yes', 'y']:
                return

        # Batch upload option
        print("\n" + "=" * 60)
        print("📦 BATCH UPLOAD OPTIONS")
        print("=" * 60)
        print("\nInstagram limit: 25 posts/day")
        print("You can upload in batches to stay under the limit.\n")

        use_batch = input("Upload in batches? (yes/no): ").strip().lower()

        if use_batch in ['yes', 'y']:
            batch_size = input("\nBatch size? (default: 10): ").strip()
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

            batch_num = input(f"\nWhich batch? (1-{total_batches}): ").strip()
            if not batch_num.isdigit() or int(batch_num) < 1 or int(batch_num) > total_batches:
                print("❌ Invalid batch number. Cancelled.")
                return

            batch_num = int(batch_num)
            start_idx = (batch_num - 1) * batch_size
            end_idx = min(start_idx + batch_size, len(videos))

            videos_to_upload = videos[start_idx:end_idx]
            dates_to_use = post_dates[start_idx:end_idx]

            print(f"\n✓ Batch {batch_num}: videos {start_idx+1}-{end_idx}")
            print(f"✓ Schedule: {dates_to_use[0]['date']} → {dates_to_use[-1]['date']}")
        else:
            videos_to_upload = videos
            dates_to_use = post_dates
            print("\n✓ Uploading all videos\n")

        # Upload
        print("\n" + "=" * 60)
        print("Starting uploads...")
        print("=" * 60)

        for idx, (video_info, date_info) in enumerate(zip(videos_to_upload, dates_to_use), 1):
            print(f"\n{'=' * 60}")
            print(f"Video {idx}/{len(videos_to_upload)}")
            print(f"{'=' * 60}")

            video_path = self.videos_folder / video_info['filename']

            if not video_path.exists():
                print(f"⚠️  Skipping {video_info['filename']} — file not found")
                self.skipped.append({'filename': video_info['filename'], 'reason': 'File not found'})
                continue

            if self.upload_video(video_info, video_path, date_info['date'], date_info['meta_time']):
                self.uploaded_count += 1

            if idx < len(videos_to_upload):
                print("\n⏳ Waiting 10 seconds before next upload...")
                time.sleep(10)

        # Final Summary
        print("\n" + "=" * 60)
        print("🎉 UPLOAD COMPLETE!")
        print("=" * 60)
        print(f"\n✅ Successfully uploaded: {self.uploaded_count}/{len(videos_to_upload)} videos")

        if self.skipped:
            print(f"\n⚠️  Issues ({len(self.skipped)} videos):")
            for item in self.skipped:
                print(f"   • {item['filename']}")
                print(f"     └─ {item['reason']}")

        if use_batch in ['yes', 'y'] and batch_num < total_batches:
            print(f"\n💡 Next batch: run again and select Batch {batch_num + 1}")

        print("\n📸 Check Meta Business Suite to verify uploads:")
        print("   https://business.facebook.com/")


def main():
    print("📸 Meta (Instagram + Facebook) Reels Upload Scheduler")
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
    print("This will upload videos to both Instagram and Facebook as Reels.")
    print("Make sure you have config/meta_config.json set up.")
    print("=" * 60)

    response = input("\nReady? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        sys.exit(0)

    uploader = MetaUploader(csv_path, videos_folder)
    uploader.run()


if __name__ == "__main__":
    main()
