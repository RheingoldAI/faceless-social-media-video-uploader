#!/usr/bin/env python3
"""
Golf Caption Refresher
Takes an existing captions CSV and generates fresh variations to avoid bot detection.
Changes captions, hashtags, and randomizes order - all without re-analyzing videos.
"""

import os
import sys
import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

# Resolve project root (parent of src/captions/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

try:
    import anthropic
except ImportError:
    print("Installing required package: anthropic...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic"])
    import anthropic


class CaptionRefresher:
    def __init__(self, input_csv):
        self.input_csv = Path(input_csv)
        self.output_csv = PROJECT_ROOT / "data" / f"golf_captions_refreshed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Get API key
        self.api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
            print("\nTo set it, run:")
            print('export ANTHROPIC_API_KEY="your-api-key-here"')
            sys.exit(1)
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def read_csv(self):
        """Read existing captions CSV"""
        videos = []
        with open(self.input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                videos.append(row)
        return videos
    
    def generate_fresh_captions(self, original_video):
        """Generate completely new caption variations"""
        
        # Extract context from original captions and filename
        original_tiktok = original_video['tiktok_caption']
        original_youtube = original_video['youtube_caption']
        filename = original_video['filename']

        original_meta = original_video.get('meta_caption', '')

        prompt = f"""You are a social media expert creating FRESH VARIATIONS of golf content captions.

ORIGINAL CONTEXT:
- Filename: {filename}
- Original TikTok: {original_tiktok}
- Original YouTube: {original_youtube}
- Original Meta (Instagram/Facebook): {original_meta}

Your task: Create COMPLETELY NEW captions that:
1. Talk about the SAME moment/video
2. Use DIFFERENT wording, angles, and hooks
3. Feel authentic and varied (not like a bot reposting)
4. Use COMPLETELY DIFFERENT hashtags

VARIATION STRATEGIES (pick different ones each time):
- Different emotional angle (shock, humor, admiration, drama, nostalgia)
- Different hook/opener
- Different focus (player, stakes, rivalry, technique, entertainment value)
- Quote imagined reactions or commentary
- Use different slang/terminology
- Reference different aspects of the same moment

TIKTOK CAPTION (100-150 characters):
- Completely different hook than original
- Different emojis (or no emojis if original had them)
- New angle on the same moment
- DO NOT use similar phrasing to original
- DO NOT include hashtags

YOUTUBE SHORTS CAPTION (80-92 characters max):
- Different keywords and phrasing
- New SEO angle
- CRITICAL: Must be 92 characters or less
- DO NOT include hashtags

META CAPTION (Instagram/Facebook Reels, 100-180 characters):
- Engaging storytelling tone — less ALL CAPS than TikTok, more personality than YouTube
- Hook that makes people stop scrolling
- 1-3 sentences, 1-3 emojis tastefully
- Can include a soft CTA (e.g. "Tag someone who needs to see this")
- DO NOT include hashtags

HASHTAGS:
- Generate 5 COMPLETELY NEW hashtags for TikTok
- Generate 5 COMPLETELY NEW hashtags for YouTube
- Generate 8 COMPLETELY NEW hashtags for Meta (3 high-reach, 3 mid-reach, 2 specific)
- DO NOT reuse hashtags from original captions
- Make them feel natural and discoverable

Return your response in this EXACT JSON format:
{{
  "tiktok_caption": "caption text here",
  "tiktok_hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"],
  "youtube_caption": "caption text here",
  "youtube_hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"],
  "meta_caption": "caption text here",
  "meta_hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8"]
}}

ONLY return the JSON, nothing else."""

        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Call Claude API
                message = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1000,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                
                response_text = message.content[0].text
                
                # Parse JSON response
                json_match = json.loads(response_text)
                
                return {
                    'tiktok_caption': json_match['tiktok_caption'],
                    'tiktok_hashtags': ' '.join(json_match['tiktok_hashtags']),
                    'youtube_caption': json_match['youtube_caption'],
                    'youtube_hashtags': ' '.join(json_match['youtube_hashtags']),
                    'meta_caption': json_match.get('meta_caption', ''),
                    'meta_hashtags': ' '.join(json_match.get('meta_hashtags', []))
                }
                
            except Exception as e:
                error_str = str(e)
                if "rate_limit" in error_str.lower():
                    retry_count += 1
                    if retry_count >= max_retries:
                        print(f"Error generating captions: {e}")
                        return None
                    
                    wait_time = 60
                    print(f"  ⏱️  Rate limit hit! Waiting {wait_time} seconds... (attempt {retry_count}/{max_retries})")
                    
                    # Show countdown
                    import time
                    for remaining in range(wait_time, 0, -10):
                        print(f"     Resuming in {remaining} seconds...", end='\r')
                        time.sleep(10)
                    
                    print(f"     Retrying now...                    ")
                    continue  # Retry
                else:
                    print(f"Error generating captions: {e}")
                    return None
    
    def refresh_captions(self):
        """Main process: read CSV, generate new captions, save to new CSV"""

        print("🔄 Golf Caption Refresher")
        print("="*60)
        print(f"\n📄 Input CSV: {self.input_csv}")

        # Read original captions
        original_videos = self.read_csv()
        print(f"✓ Found {len(original_videos)} videos")

        # Randomize order
        random.shuffle(original_videos)
        print("✓ Randomized video order")

        print("\n" + "="*60)
        print("Generating fresh captions...")
        print("="*60)

        refreshed_videos = []

        for idx, video in enumerate(original_videos, 1):
            print(f"\n[{idx}/{len(original_videos)}] {video['filename']}")

            # Generate new captions
            print("  ✍️  Generating fresh variations...")
            new_captions = self.generate_fresh_captions(video)

            if new_captions:
                refreshed_video = {
                    'filename': video['filename'],
                    'tiktok_caption': new_captions['tiktok_caption'],
                    'tiktok_hashtags': new_captions['tiktok_hashtags'],
                    'youtube_caption': new_captions['youtube_caption'],
                    'youtube_hashtags': new_captions['youtube_hashtags'],
                    'meta_caption': new_captions['meta_caption'],
                    'meta_hashtags': new_captions['meta_hashtags']
                }
                refreshed_videos.append(refreshed_video)
                print(f"  ✅ Done!")
            else:
                print(f"  ❌ Failed to generate new captions")
                # Keep original as fallback
                refreshed_videos.append(video)

        # Save to new CSV
        print("\n" + "="*60)
        print("Saving refreshed captions...")
        print("="*60)

        fieldnames = [
            'filename', 'tiktok_caption', 'tiktok_hashtags',
            'youtube_caption', 'youtube_hashtags',
            'meta_caption', 'meta_hashtags'
        ]

        with open(self.output_csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(refreshed_videos)

        print(f"\n✅ Saved to: {self.output_csv}")
        print("\n" + "="*60)
        print("🎉 REFRESH COMPLETE!")
        print("="*60)
        print(f"\n📊 Summary:")
        print(f"   • {len(refreshed_videos)} videos refreshed")
        print(f"   • New captions generated")
        print(f"   • New hashtags generated")
        print(f"   • Order randomized")
        print(f"\n📄 New CSV: {self.output_csv.name}")


def main():
    print("🔄 Golf Caption Refresher")
    print("="*60)
    print("\nThis tool creates fresh caption variations from your existing CSV.")
    print("It will:")
    print("  • Generate completely new captions for the same videos")
    print("  • Create all-new hashtags")
    print("  • Randomize the posting order")
    print("  • Generate a new posting schedule")
    print("  • Save to a new CSV file (keeps original intact)")
    print("\nThis avoids bot detection and saves API costs vs re-analyzing videos!")
    print("="*60)
    
    # Get input CSV
    if len(sys.argv) > 1:
        input_csv = sys.argv[1]
    else:
        input_csv = input("\nPath to existing CSV (or press Enter for 'golf_captions.csv'): ").strip()
        if not input_csv:
            input_csv = str(PROJECT_ROOT / "data" / "golf_captions.csv")
    
    if not os.path.exists(input_csv):
        print(f"❌ Error: File not found: {input_csv}")
        sys.exit(1)
    
    response = input("\nReady to generate fresh captions? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        sys.exit(0)
    
    refresher = CaptionRefresher(input_csv)
    refresher.refresh_captions()


if __name__ == "__main__":
    main()
