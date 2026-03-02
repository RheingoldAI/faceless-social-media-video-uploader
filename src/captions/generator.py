#!/usr/bin/env python3
"""
Golf Video Caption Generator
Analyzes golf shot videos, searches for context, and generates optimized captions
for TikTok and YouTube Shorts with strategic hashtags.
"""

import os
import sys
import csv
import json
import base64
import re
import random
import time
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

try:
    import cv2
except ImportError:
    print("Installing required package: opencv-python...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python"])
    import cv2


class GolfCaptionGenerator:
    def __init__(self, video_folder):
        self.video_folder = Path(video_folder)
        self.client = anthropic.Anthropic()
        self.output_csv = str(PROJECT_ROOT / "data" / "golf_captions.csv")
    
    def parse_filename(self, filename):
        """Extract player, content type, tournament/event, and year from filename"""
        # Remove extension and version
        name = filename.stem
        parts = name.split('_')
        
        if len(parts) >= 3:
            player = parts[0].replace('_', ' ')
            content_type = parts[1].replace('_', ' ')  # Could be shot type, interview, moment, etc.
            event_year = parts[2]
            
            # Extract year (last 4 digits) and event/tournament
            year_match = re.search(r'(\d{4})', event_year)
            if year_match:
                year = year_match.group(1)
                event = event_year.replace(year, '')
            else:
                year = "Unknown"
                event = event_year
            
            return {
                'player': player,
                'content_type': content_type,
                'event': event,
                'year': year
            }
        
        return None
    
    def extract_frame(self, video_path):
        """Extract a frame from the middle of the video"""
        try:
            cap = cv2.VideoCapture(str(video_path))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Get frame from middle of video
            cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                # Save temporary frame
                temp_path = "/tmp/temp_frame.jpg"
                cv2.imwrite(temp_path, frame)
                
                # Convert to base64
                with open(temp_path, "rb") as f:
                    image_data = base64.standard_b64encode(f.read()).decode("utf-8")
                
                os.remove(temp_path)
                return image_data
            
        except Exception as e:
            print(f"Error extracting frame: {e}")
        
        return None
    
    def search_web_context(self, player, content_type, event, year):
        """Search for context about the video content"""
        query = f"{player} {content_type} {year} {event} golf"
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                message = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    tools=[{
                        "type": "web_search_20250305",
                        "name": "web_search"
                    }],
                    messages=[{
                        "role": "user",
                        "content": f"""Search for information about this golf moment: {query}. 

This could be:
- A golf shot (bunker shot, chip, drive, putt, etc.)
- An interview or press conference moment
- A celebration or reaction
- An interaction between players
- A celebrity playing golf
- Any other memorable golf moment

Find details about:
- The context of the event/tournament (if applicable)
- What made this moment significant or memorable
- The stakes or importance at the time
- Any dramatic or interesting background
- Whether this involves a PGA Tour pro or a celebrity/amateur

Provide enough context to make an exciting social media caption."""
                    }]
                )
                break  # Success, exit retry loop
            
            except Exception as e:
                error_str = str(e)
                if "rate_limit" in error_str.lower():
                    retry_count += 1
                    if retry_count >= max_retries:
                        print(f"Error searching web: {e}")
                        return "No additional context found."
                    
                    wait_time = 60
                    print(f"  ⏱️  Rate limit hit! Waiting {wait_time} seconds... (attempt {retry_count}/{max_retries})")
                    
                    # Show countdown
                    for remaining in range(wait_time, 0, -10):
                        print(f"     Resuming in {remaining} seconds...", end='\r')
                        time.sleep(10)
                    
                    print(f"     Retrying now...                    ")
                    continue  # Retry
                else:
                    print(f"Error searching web: {e}")
                    return "No additional context found."
        
        # Extract search results and text (after successful retry loop)
        context = ""
        for block in message.content:
            if block.type == "text":
                context += block.text + "\n"
        
        return context if context else "No additional context found."
    
    def generate_captions(self, video_info, web_context, image_data=None):
        """Generate platform-specific captions using Claude"""
        
        content = [
            {
                "type": "text",
                "text": f"""You are an excited golf fan creating social media captions for amazing golf content!

VIDEO INFO:
- Person/Player: {video_info['player']}
- Content Type: {video_info['content_type']} (this could be a shot, interview, celebration, interaction, or any golf moment)
- Event/Tournament: {video_info['event']}
- Year: {video_info['year']}

CONTEXT FROM WEB SEARCH:
{web_context}

IMPORTANT CONTEXT:
- This person could be a PGA Tour professional OR a celebrity/amateur golfer
- The content might be a golf shot, but could also be an interview, funny moment, celebration, interaction, or any memorable golf content
- Adjust your caption style based on what this actually is

Generate THREE captions (TikTok, YouTube Shorts, and Meta/Instagram/Facebook Reels) with the following requirements:

TIKTOK CAPTION:
- Start with an attention-grabbing hook (first 1-2 sentences MUST make people stop scrolling)
- Excited fan energy with some emojis (don't overdo it)
- Casual, conversational tone
- Highlight what makes this moment special/entertaining/dramatic
- If it's a celebrity, play up the entertainment value
- If it's a pro, play up the skill/stakes/drama
- 100-150 characters max
- Include exactly 5 strategic hashtags (mix of trending golf hashtags, person-specific, and content-type-specific)

YOUTUBE SHORTS CAPTION:
- Concise and punchy - keyword-rich for SEO
- Include person's name and key moment/context
- Front-load the most important info
- Professional but engaging tone
- 80-92 characters max (CRITICAL: must leave room for " #Shorts" tag)
- Include exactly 5 hashtags (focused on searchability - person, event, golf terms, content type)

META CAPTION (Instagram Reels + Facebook Reels via Meta Business Suite):
- Engaging storytelling tone — less ALL CAPS clickbait than TikTok, more personality than YouTube
- Open with a hook that makes people stop scrolling
- Include context that makes even non-golfers interested
- 1-3 sentences max (100-180 characters ideal)
- Use 1-3 emojis tastefully (not overloaded)
- End with a soft CTA when natural (e.g. "Tag someone who needs to see this")
- Include exactly 8 hashtags (3 high-reach like #Golf #GolfReels, 3 mid-reach, 2 specific)

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
            }
        ]
        
        # Add image if available
        if image_data:
            content.insert(0, {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_data
                }
            })
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                message = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,
                    messages=[{
                        "role": "user",
                        "content": content
                    }]
                )
                break  # Success, exit retry loop
            
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
                    for remaining in range(wait_time, 0, -10):
                        print(f"     Resuming in {remaining} seconds...", end='\r')
                        time.sleep(10)
                    
                    print(f"     Retrying now...                    ")
                    continue  # Retry
                else:
                    print(f"Error generating captions: {e}")
                    return None
        
        # Parse response (after successful retry loop)
        response_text = message.content[0].text
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            captions = json.loads(json_match.group())
            return captions
        else:
            print("Could not parse JSON from response")
            return None
    
    def process_videos(self):
        """Process all videos in the folder"""
        # Get all video files
        video_extensions = ['.mp4', '.mov', '.avi', '.MP4', '.MOV']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(self.video_folder.glob(f'*{ext}'))
        
        video_files = sorted(video_files)
        
        # Randomize the order for posting variety
        random.shuffle(video_files)
        print(f"🔀 Videos will be randomized for posting schedule\n")
        if not video_files:
            print(f"No video files found in {self.video_folder}")
            return
        
        print(f"Found {len(video_files)} videos to process\n")
        
        results = []
        
        for idx, video_path in enumerate(video_files, 1):
            print(f"Processing {idx}/{len(video_files)}: {video_path.name}")
            
            # Parse filename
            video_info = self.parse_filename(video_path)
            if not video_info:
                print(f"  ⚠️  Could not parse filename: {video_path.name}")
                continue
            
            print(f"  📹 Person/Player: {video_info['player']}")
            print(f"  🎬 Content: {video_info['content_type']}")
            print(f"  🏆 Event: {video_info['year']} {video_info['event']}")
            
            # Extract frame
            print("  📸 Extracting frame...")
            image_data = self.extract_frame(video_path)
            
            # Search for context
            print("  🔍 Searching for context...")
            web_context = self.search_web_context(
                video_info['player'],
                video_info['content_type'],
                video_info['event'],
                video_info['year']
            )
            
            # Generate captions
            print("  ✍️  Generating captions...")
            captions = self.generate_captions(video_info, web_context, image_data)
            
            if captions:
                results.append({
                    'filename': video_path.name,
                    'tiktok_caption': captions['tiktok_caption'],
                    'tiktok_hashtags': ' '.join(captions['tiktok_hashtags']),
                    'youtube_caption': captions['youtube_caption'],
                    'youtube_hashtags': ' '.join(captions['youtube_hashtags']),
                    'meta_caption': captions.get('meta_caption', ''),
                    'meta_hashtags': ' '.join(captions.get('meta_hashtags', []))
                })

                print(f"  ✅ Done!")
            else:
                print("  ❌ Failed to generate captions")
            
            print()
        
        # Save to CSV
        self.save_to_csv(results)
        print(f"\n🎉 Complete! Processed {len(results)} videos")
        print(f"📄 Results saved to: {self.output_csv}")
    
    def save_to_csv(self, results):
        """Save results to CSV file"""
        if not results:
            return
        
        fieldnames = [
            'filename', 'tiktok_caption', 'tiktok_hashtags',
            'youtube_caption', 'youtube_hashtags',
            'meta_caption', 'meta_hashtags'
        ]
        
        with open(self.output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)


def main():
    print("🏌️ Golf Video Caption Generator 🏌️")
    print("=" * 50)
    
    # Get video folder from user
    if len(sys.argv) > 1:
        video_folder = sys.argv[1]
    else:
        video_folder = input("\nEnter the path to your video folder: ").strip()
    
    if not os.path.exists(video_folder):
        print(f"❌ Error: Folder not found: {video_folder}")
        sys.exit(1)
    
    print(f"\n📁 Video folder: {video_folder}")
    print("\nThis will:")
    print("  1. Analyze each video frame")
    print("  2. Search the web for tournament context")
    print("  3. Generate optimized captions for TikTok and YouTube Shorts")
    print("  4. Create a posting schedule (daily, skipping Sundays)")
    print("  5. Save everything to a CSV file for review")
    
    response = input("\nReady to start? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        sys.exit(0)
    
    print("\n" + "=" * 50)
    print("Starting processing...\n")
    
    generator = GolfCaptionGenerator(video_folder)
    generator.process_videos()


if __name__ == "__main__":
    main()
