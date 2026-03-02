#!/usr/bin/env python3
"""
YouTube Shorts Upload Scheduler
Automates uploading and scheduling YouTube Shorts using the YouTube Data API v3.
Dates are calculated dynamically at runtime from config/posting_schedule.json.
"""

import os
import sys
import csv
import json
import pickle
import time
from pathlib import Path
from datetime import datetime, timedelta
import subprocess

# Resolve project root (parent of src/uploaders/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("Installing required Google API packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade",
                          "google-api-python-client", "google-auth-httplib2",
                          "google-auth-oauthlib"])
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


def load_posting_schedule():
    """Load day-of-week posting times from config."""
    schedule_path = PROJECT_ROOT / 'config' / 'posting_schedule.json'
    with open(schedule_path, 'r') as f:
        return json.load(f)


def calculate_post_dates(num_videos, schedule, start_date=None):
    """Calculate posting dates for N videos starting from tomorrow.

    Skips any day not listed in the schedule config.
    Returns a list of dicts: [{'date': '2026-02-28', 'weekday': 'Friday', 'time': '16:00'}, ...]
    """
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
                'youtube_time': schedule[weekday_name]['youtube'],
                'tiktok_time': schedule[weekday_name]['tiktok'],
            })
        current_date += timedelta(days=1)

    return dates


class YouTubeUploader:
    def __init__(self, csv_path, videos_folder, credentials_file):
        self.csv_path = Path(csv_path)
        self.videos_folder = Path(videos_folder)
        self.credentials_file = Path(credentials_file)
        self.token_file = PROJECT_ROOT / 'config' / 'youtube_token.pickle'
        self.uploaded_count = 0
        self.skipped = []  # Track skipped/failed videos with reasons
        self.youtube = None
        self.schedule = load_posting_schedule()

    def authenticate(self):
        """Authenticate with YouTube API"""
        print("\n🔐 Authenticating with YouTube...")

        creds = None

        # Load existing token if available
        if self.token_file.exists():
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("   → Refreshing access token...")
                creds.refresh(Request())
            else:
                print("   → Opening browser for authorization...")
                print("   → Please authorize the app in your browser")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials for next time
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)

        self.youtube = build('youtube', 'v3', credentials=creds)
        print("   ✓ Authentication successful!")

    def read_csv(self):
        """Read the captions CSV file"""
        videos = []
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                videos.append(row)
        return videos

    def upload_video(self, video_info, video_path, post_date, post_time):
        """Upload a single video to YouTube with a calculated schedule date/time.

        Returns True on success, False on failure. Never raises — all errors
        are caught, logged, and added to self.skipped so the batch continues.
        """
        filename = video_info['filename']

        try:
            print(f"\n📤 Uploading: {filename}")
            print(f"   Title: {video_info['youtube_caption'][:50]}...")
            print(f"   Schedule: {post_date} at {post_time}")

            # Prepare video metadata
            # YouTube title limit: 100 characters (including #Shorts)
            caption = video_info['youtube_caption']

            # Reserve 8 characters for " #Shorts"
            max_caption_length = 92
            if len(caption) > max_caption_length:
                caption = caption[:max_caption_length].strip()

            title = f"{caption} #Shorts"
            description = f"{video_info['youtube_hashtags']}"

            # Validate title length
            if len(title) > 100:
                print(f"   ⚠️  Title too long ({len(title)} chars), truncating...")
                title = title[:100]

            print(f"   → Final title ({len(title)} chars): {title}")

            # Parse schedule time
            schedule_datetime = datetime.strptime(f"{post_date} {post_time}", "%Y-%m-%d %H:%M")

            # Convert to ISO 8601 format (YouTube's required format)
            publish_at = schedule_datetime.strftime("%Y-%m-%dT%H:%M:%S.000Z")

            # Video metadata
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': [tag.strip('#') for tag in video_info['youtube_hashtags'].split() if tag.startswith('#')],
                    'categoryId': '17',  # Sports category
                },
                'status': {
                    'privacyStatus': 'private',  # Must be private for scheduled videos
                    'publishAt': publish_at,
                    'selfDeclaredMadeForKids': False
                }
            }

            # Upload video file with retry logic
            print("   → Uploading video file...")

            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    media = MediaFileUpload(
                        str(video_path),
                        chunksize=1024*1024,  # 1MB chunks
                        resumable=True,
                        mimetype='video/*'
                    )

                    request = self.youtube.videos().insert(
                        part='snippet,status',
                        body=body,
                        media_body=media
                    )

                    response = None
                    while response is None:
                        status, response = request.next_chunk()
                        if status:
                            progress = int(status.progress() * 100)
                            print(f"   → Upload progress: {progress}%")

                    video_id = response['id']
                    print(f"   ✓ Video uploaded! ID: {video_id}")
                    print(f"   ✓ Scheduled for: {post_date} at {post_time}")

                    # --- Check for YouTube restrictions/flags ---
                    upload_status = response.get('status', {}).get('uploadStatus', '')
                    rejection_reason = response.get('status', {}).get('rejectionReason', '')
                    failure_reason = response.get('status', {}).get('failureReason', '')

                    if rejection_reason:
                        reason = f"REJECTED — {rejection_reason}"
                        print(f"   ⚠️  YouTube flagged this video: {reason}")
                        print(f"   ⚠️  Video ID {video_id} may not publish. Check YouTube Studio.")
                        self.skipped.append({'filename': filename, 'reason': reason, 'video_id': video_id})
                        return True  # Still uploaded, just flagged

                    if failure_reason:
                        reason = f"PROCESSING FAILURE — {failure_reason}"
                        print(f"   ⚠️  YouTube processing issue: {reason}")
                        print(f"   ⚠️  Video ID {video_id} may need attention. Check YouTube Studio.")
                        self.skipped.append({'filename': filename, 'reason': reason, 'video_id': video_id})
                        return True  # Still uploaded, just flagged

                    if upload_status and upload_status not in ('uploaded', 'processed'):
                        reason = f"Unexpected upload status: {upload_status}"
                        print(f"   ⚠️  {reason}")
                        self.skipped.append({'filename': filename, 'reason': reason, 'video_id': video_id})

                    return True

                except Exception as e:
                    error_str = str(e)

                    # Check if it's a quota/rate limit error (retryable)
                    if "quota" in error_str.lower() or "rate" in error_str.lower() or "429" in error_str:
                        retry_count += 1
                        if retry_count >= max_retries:
                            reason = f"Quota/rate limit after {max_retries} retries: {e}"
                            print(f"   ❌ {reason}")
                            self.skipped.append({'filename': filename, 'reason': reason})
                            return False

                        wait_time = 120  # 2 minutes for temporary rate limits
                        print(f"   ⏱️  Rate/Quota limit hit! Waiting {wait_time} seconds... (attempt {retry_count}/{max_retries})")

                        for remaining in range(wait_time, 0, -30):
                            print(f"     Resuming in {remaining} seconds...", end='\r')
                            time.sleep(30)

                        print(f"     Retrying upload...                    ")
                        continue  # Retry
                    else:
                        # Non-retryable upload error — log and move on
                        reason = f"Upload error: {e}"
                        print(f"   ❌ {reason}")
                        self.skipped.append({'filename': filename, 'reason': reason})
                        return False

        except Exception as e:
            # Catch-all for anything unexpected (bad CSV data, path issues, etc.)
            reason = f"Unexpected error: {e}"
            print(f"   ❌ {reason}")
            self.skipped.append({'filename': filename, 'reason': reason})
            return False

    def run(self):
        """Main execution"""
        print("📺 YouTube Shorts Upload Scheduler")
        print("="*60)

        # Authenticate
        try:
            self.authenticate()
        except Exception as e:
            print(f"\n❌ Authentication failed: {e}")
            print("\nMake sure:")
            print("  1. You have the correct credentials JSON file")
            print("  2. You authorized the app in your browser")
            return

        # Read CSV
        print(f"\n📄 Reading CSV: {self.csv_path}")
        videos = self.read_csv()
        print(f"✓ Found {len(videos)} videos to upload")

        # Calculate posting dates for ALL videos
        post_dates = calculate_post_dates(len(videos), self.schedule)

        print(f"\n📅 Schedule preview (first video → last video):")
        print(f"   Starts: {post_dates[0]['date']} ({post_dates[0]['weekday']})")
        print(f"   Ends:   {post_dates[-1]['date']} ({post_dates[-1]['weekday']})")

        # Verify video files
        print(f"\n📁 Checking video files in: {self.videos_folder}")
        missing = []
        for video in videos:
            if not (self.videos_folder / video['filename']).exists():
                missing.append(video['filename'])

        if missing:
            print("\n⚠️  WARNING: Missing videos:")
            for f in missing:
                print(f"   - {f}")
            response = input("\nContinue? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                return

        # BATCH UPLOAD OPTION
        print("\n" + "="*60)
        print("📦 BATCH UPLOAD OPTIONS")
        print("="*60)
        print("\nYouTube has a daily upload quota (~10-12 videos/day)")
        print("You can upload in batches to stay under the limit.\n")

        use_batch = input("Do you want to upload in batches? (yes/no): ").strip().lower()

        if use_batch in ['yes', 'y']:
            batch_size = input("\nHow many videos per batch? (default: 10): ").strip()
            batch_size = int(batch_size) if batch_size.isdigit() else 10

            # Calculate total batches
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

            # Ask which batch to upload
            print(f"\n" + "="*60)
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
            print("\n✓ Uploading all videos\n")

        # Upload videos
        print("\n" + "="*60)
        print("Starting uploads...")
        print("="*60)

        for idx, (video_info, date_info) in enumerate(zip(videos_to_upload, dates_to_use), 1):
            print(f"\n{'='*60}")
            print(f"Video {idx}/{len(videos_to_upload)}")
            print(f"{'='*60}")

            video_path = self.videos_folder / video_info['filename']

            if not video_path.exists():
                print(f"⚠️  Skipping {video_info['filename']} — file not found")
                self.skipped.append({'filename': video_info['filename'], 'reason': 'File not found'})
                continue

            if self.upload_video(video_info, video_path, date_info['date'], date_info['youtube_time']):
                self.uploaded_count += 1

            # Always continue to the next video regardless of success/failure

        # ── Final Summary ──
        print("\n" + "="*60)
        print("🎉 UPLOAD COMPLETE!")
        print("="*60)
        print(f"\n✅ Successfully uploaded: {self.uploaded_count}/{len(videos_to_upload)} videos")

        if self.skipped:
            print(f"\n⚠️  Issues ({len(self.skipped)} videos):")
            for item in self.skipped:
                vid_id = item.get('video_id', '')
                vid_id_str = f" (ID: {vid_id})" if vid_id else ""
                print(f"   • {item['filename']}{vid_id_str}")
                print(f"     └─ {item['reason']}")
            print(f"\n   💡 Check YouTube Studio for flagged videos:")
            print(f"      https://studio.youtube.com/")

        if use_batch in ['yes', 'y'] and batch_num < total_batches:
            print(f"\n💡 TIP: To upload the next batch, run this script again tomorrow")
            print(f"    and select Batch {batch_num + 1}")

        print("\n📺 Check your YouTube Studio to verify scheduled uploads:")
        print("   https://studio.youtube.com/")


def main():
    print("📺 YouTube Shorts Upload Scheduler")
    print("="*60)

    # Get CSV path
    csv_path = str(PROJECT_ROOT / "data" / "golf_captions.csv")
    if not os.path.exists(csv_path):
        csv_path = input("\nCSV file path: ").strip()
        if not os.path.exists(csv_path):
            print(f"❌ Not found: {csv_path}")
            sys.exit(1)

    print(f"\n✓ CSV: {csv_path}")

    # Get videos folder
    if len(sys.argv) > 1:
        videos_folder = sys.argv[1]
    else:
        videos_folder = str(PROJECT_ROOT / "videos")

    if not os.path.exists(videos_folder):
        print(f"❌ Not found: {videos_folder}")
        sys.exit(1)

    print(f"✓ Videos: {videos_folder}")

    # Get credentials file
    credentials_files = list((PROJECT_ROOT / 'config').glob('client_secret*.json'))
    if credentials_files:
        credentials_file = credentials_files[0]
        print(f"✓ Found credentials: {credentials_file}")
    else:
        credentials_file = input("\nPath to OAuth credentials JSON file: ").strip()
        if not os.path.exists(credentials_file):
            print(f"❌ Not found: {credentials_file}")
            sys.exit(1)

    # Load schedule to show preview
    schedule = load_posting_schedule()
    print(f"\n📅 Posting schedule loaded ({len(schedule)} days/week)")

    print("\n" + "="*60)
    print("This will:")
    print("  1. Authenticate with your YouTube account")
    print("  2. Upload all videos from the CSV")
    print("  3. Schedule them dynamically starting from tomorrow")
    print("\nNote: Videos will be set to 'Private' until scheduled time")
    print("="*60)

    response = input("\nReady? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        sys.exit(0)

    uploader = YouTubeUploader(csv_path, videos_folder, credentials_file)
    uploader.run()


if __name__ == "__main__":
    main()
