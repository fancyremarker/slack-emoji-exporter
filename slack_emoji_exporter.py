#!/usr/bin/env python3
"""
Slack Emoji Exporter - Export custom emojis from one Slack workspace to another

This script allows you to:
1. List all custom emojis from a source Slack workspace
2. Download all emoji images
3. Upload the emojis to a destination Slack workspace

Authentication is handled via:
- Source workspace: Slack API token (User or Bot token with emoji:read scope)
- Destination workspace: Session cookie (from browser) for uploading emojis
"""

import argparse
import os
import sys
import json
import time
import random
import requests
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

# Default paths
DEFAULT_OUTPUT_DIR = "emoji_downloads"

def setup_argparse():
    """Configure command-line argument parsing"""
    parser = argparse.ArgumentParser(description="Export Slack emojis from one workspace to another")
    
    # Common arguments
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                      help=f"Directory to save emoji files (default: {DEFAULT_OUTPUT_DIR})")
    
    # Create subparsers for different operations
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all custom emojis in a Slack workspace")
    list_parser.add_argument("--source-token", required=True,
                           help="Slack API token for the source workspace (starts with xoxp- or xoxb-)")
    list_parser.add_argument("--output-file", default="emoji_list.json",
                           help="JSON file to save emoji list (default: emoji_list.json)")
    
    # Download command
    download_parser = subparsers.add_parser("download", help="Download emoji images from a Slack workspace")
    download_parser.add_argument("--source-token", required=True,
                              help="Slack API token for the source workspace (starts with xoxp- or xoxb-)")
    download_parser.add_argument("--emoji-list", default="emoji_list.json", 
                               help="JSON file with emoji list (default: emoji_list.json)")
    
    # Upload command
    upload_parser = subparsers.add_parser("upload", help="Upload emoji images to a Slack workspace")
    upload_parser.add_argument("--cookie", required=True,
                            help="Session cookie from Slack web interface (from browser developer tools)")
    upload_parser.add_argument("--token", required=True,
                            help="xoxc token from Slack web interface (from browser developer tools)")
    upload_parser.add_argument("--team-id", required=True,
                            help="Team ID of destination Slack workspace (e.g., T012AB3C4)")
    upload_parser.add_argument("--emoji-dir", default=DEFAULT_OUTPUT_DIR, 
                             help=f"Directory with emoji files to upload (default: {DEFAULT_OUTPUT_DIR})")
    
    # All-in-one command
    export_parser = subparsers.add_parser("export", help="Export all emojis from source to destination workspace")
    export_parser.add_argument("--source-token", required=True,
                             help="Slack API token for the source workspace (starts with xoxp- or xoxb-)")
    export_parser.add_argument("--cookie", required=True,
                             help="Session cookie from Slack web interface for destination (from browser developer tools)")
    export_parser.add_argument("--team-id", required=True,
                             help="Team ID of destination Slack workspace (e.g., T012AB3C4)")
    
    return parser

def list_emojis(token, output_file):
    """List all custom emojis in a Slack workspace and save to a file"""
    url = "https://slack.com/api/emoji.list"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    if not response.ok:
        print(f"Error fetching emojis: {response.status_code} {response.text}")
        sys.exit(1)
        
    data = response.json()
    if not data.get("ok"):
        print(f"Slack API Error: {data.get('error', 'Unknown error')}")
        sys.exit(1)
        
    # Filter out alias emojis (those that point to other emojis)
    custom_emojis = {}
    for name, url in data["emoji"].items():
        if not url.startswith("alias:"):
            custom_emojis[name] = url
            
    # Save the emoji list to a file
    with open(output_file, "w") as f:
        json.dump(custom_emojis, f, indent=2)
        
    print(f"Found {len(custom_emojis)} custom emojis (excluding aliases)")
    print(f"Emoji list saved to {output_file}")
    
    return custom_emojis

def download_emoji(name, url, output_dir):
    """Download a single emoji image"""
    if url.startswith("alias:"):
        return None
        
    # Parse URL to get file extension
    parsed_url = urlparse(url)
    path = parsed_url.path
    extension = os.path.splitext(path)[1]
    if not extension:
        extension = ".png"  # Default to PNG if no extension found
        
    output_file = os.path.join(output_dir, f"{name}{extension}")
    
    try:
        response = requests.get(url, stream=True)
        if response.ok:
            with open(output_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
            return name, output_file
        else:
            print(f"Error downloading {name}: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error downloading {name}: {e}")
        return None

def download_emojis(emoji_list, output_dir):
    """Download all emoji images in parallel"""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load emoji list from file if it's a string
    if isinstance(emoji_list, str):
        try:
            with open(emoji_list, "r") as f:
                emoji_list = json.load(f)
        except Exception as e:
            print(f"Error loading emoji list: {e}")
            sys.exit(1)
    
    print(f"Downloading {len(emoji_list)} emojis to {output_dir}...")
    
    downloaded = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for name, url in emoji_list.items():
            futures.append(executor.submit(download_emoji, name, url, output_dir))
            
        for future in futures:
            result = future.result()
            if result:
                downloaded.append(result)
                
    print(f"Downloaded {len(downloaded)} emojis")
    return downloaded

def upload_emoji(team_id, cookie, token, name, file_path):
    """Upload a single emoji to a Slack workspace"""
    url = f"https://{team_id}.slack.com/api/emoji.add"
    
    headers = {
        "Cookie": cookie,
    }
    
    backoff = 1
    max_retries = 5
    attempts = 0

    while attempts < max_retries:
        attempts += 1
        
        # Open the file for each attempt to ensure a fresh connection
        with open(file_path, "rb") as f:
            files = {
                "image": f,
                "mode": (None, "data"),
                "name": (None, name),
            }

            data = {
                "token": token
            }

            # Create a new session for each attempt to avoid connection-based rate limiting
            with requests.Session() as session:
                response = session.post(url, data=data, headers=headers, files=files)

                if response.ok:
                    data = response.json()
                    if data.get("ok"):
                        print(f"✓ Uploaded: {name}")
                        return True
                    else:
                        error = data.get("error", "Unknown error")
                        if error == "ratelimited":
                            print(f"✗ Rate limited uploading {name}. Retrying with new connection in {backoff} seconds...")
                            time.sleep(backoff)
                            backoff *= 2
                            continue
                        else:
                            print(f"✗ Error uploading {name}: {error}")
                            return False
                elif response.status_code == 429:
                    print(f"✗ Rate limited uploading {name}: {response.status_code}. Retrying with new connection in {backoff} seconds...")
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    print(f"✗ Error uploading {name}: {response.status_code} {response.text}")
                    if attempts < max_retries:
                        print(f"    Retrying with new connection in {backoff} seconds...")
                        time.sleep(backoff)
                        backoff *= 2
                    else:
                        print(f"    Max retries reached. Giving up on {name}.")
                        return False

    return False

def upload_emojis(team_id, cookie, token, emoji_dir):
    """Upload emoji images to a Slack workspace"""
    # Get list of emoji files
    emoji_files = []
    for ext in ["*.png", "*.jpg", "*.jpeg", "*.gif"]:
        emoji_files.extend(Path(emoji_dir).glob(ext))
    
    print(f"Found {len(emoji_files)} emoji files in {emoji_dir}")
    
    uploaded = 0
    failed = 0

    # Use jittered delays between uploads

    for file_path in emoji_files:
        name = file_path.stem
        print(f"Uploading {name}... ", end="", flush=True)
        
        if upload_emoji(team_id, cookie, token, name, file_path):
            uploaded += 1
        else:
            failed += 1
            
        # Add a delay with jitter to avoid rate limiting
        delay = 1 + random.uniform(0.5, 2.0)
        time.sleep(delay)
    
    print(f"Uploaded {uploaded} emojis, failed {failed} emojis")
    return uploaded

def main():
    """Main entry point for the script"""
    parser = setup_argparse()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    if args.command == "list":
        list_emojis(args.source_token, args.output_file)
        
    elif args.command == "download":
        # Check if emoji list file exists, if not, fetch it first
        if not os.path.exists(args.emoji_list):
            print(f"Emoji list file {args.emoji_list} not found, fetching it first...")
            emoji_list = list_emojis(args.source_token, args.emoji_list)
        else:
            with open(args.emoji_list, "r") as f:
                emoji_list = json.load(f)
        download_emojis(emoji_list, args.output_dir)
        
    elif args.command == "upload":
        upload_emojis(args.team_id, args.cookie, args.token, args.emoji_dir)
        
    elif args.command == "export":
        # Run all steps
        emoji_list = list_emojis(args.source_token, "emoji_list.json")
        download_emojis(emoji_list, args.output_dir)
        upload_emojis(args.team_id, args.cookie, args.token, args.output_dir)

if __name__ == "__main__":
    main()