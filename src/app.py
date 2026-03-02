#!/usr/bin/env python3
"""
Golf Video Automation - Master Control Panel
Beautiful terminal UI for managing your entire golf video automation workflow
"""

import os
import sys
import subprocess
from pathlib import Path

# Resolve project root (parent of src/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich import box
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.layout import Layout
    from rich.text import Text
except ImportError:
    print("Installing required UI package...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich import box
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.layout import Layout
    from rich.text import Text

console = Console()


class GolfAutomationUI:
    def __init__(self):
        self.video_folder = None
        self.csv_file = str(PROJECT_ROOT / "data" / "golf_captions.csv")
        
    def show_banner(self):
        """Display welcome banner"""
        banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║       🏌️  GOLF VIDEO AUTOMATION CONTROL PANEL  ⛳           ║
║                                                               ║
║            Automate Your Golf Content Empire                  ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
        """
        console.print(banner, style="bold cyan")
    
    def show_main_menu(self):
        """Display main menu and get user choice"""
        
        menu = Table(show_header=False, box=box.ROUNDED, border_style="cyan")
        menu.add_column("Option", style="bold yellow", width=8)
        menu.add_column("Description", style="white")
        
        menu.add_row("1", "🎬 Generate Captions (from videos)")
        menu.add_row("2", "🔄 Refresh Captions (create variations)")
        menu.add_row("3", "📺 Upload to YouTube")
        menu.add_row("4", "📱 Upload to TikTok")
        menu.add_row("5", "📸 Upload to Meta (Instagram + Facebook)")
        menu.add_row("6", "🔧 Full Workflow (Generate → Upload)")
        menu.add_row("7", "📊 View Current Schedule")
        menu.add_row("8", "⚙️  Settings")
        menu.add_row("0", "🚪 Exit")
        
        console.print(Panel(menu, title="[bold cyan]Main Menu[/bold cyan]", border_style="cyan"))
        
        choice = Prompt.ask(
            "\n[bold yellow]Select an option[/bold yellow]",
            choices=["0", "1", "2", "3", "4", "5", "6", "7", "8"],
            default="1"
        )
        
        return choice
    
    def get_video_folder(self):
        """Get video folder from user"""
        if self.video_folder:
            use_existing = Confirm.ask(
                f"\n[cyan]Use existing folder: {self.video_folder}?[/cyan]",
                default=True
            )
            if use_existing:
                return self.video_folder
        
        console.print("\n[bold yellow]📁 Video Folder Setup[/bold yellow]")
        folder = Prompt.ask(
            "[cyan]Enter path to your video folder[/cyan]",
            default=str(PROJECT_ROOT / "videos")
        )
        
        if not os.path.exists(folder):
            console.print(f"[bold red]❌ Folder not found: {folder}[/bold red]")
            return None
        
        # Count videos
        video_count = len(list(Path(folder).glob('*.mp4'))) + len(list(Path(folder).glob('*.mov')))
        console.print(f"[bold green]✓ Found {video_count} videos[/bold green]")
        
        self.video_folder = folder
        return folder
    
    def generate_captions(self):
        """Run caption generator"""
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold yellow]🎬 CAPTION GENERATOR[/bold yellow]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
        
        folder = self.get_video_folder()
        if not folder:
            return
        
        console.print("\n[dim]This will:[/dim]")
        console.print("[dim]  • Analyze each video[/dim]")
        console.print("[dim]  • Search web for context[/dim]")
        console.print("[dim]  • Generate TikTok + YouTube captions[/dim]")
        console.print("[dim]  • Create posting schedule[/dim]")
        console.print("[dim]  • Save to CSV[/dim]\n")
        
        if not Confirm.ask("[yellow]Ready to generate captions?[/yellow]", default=True):
            return
        
        console.print("\n[bold green]🚀 Starting caption generator...[/bold green]\n")
        
        try:
            subprocess.run([sys.executable, str(PROJECT_ROOT / "src" / "captions" / "generator.py"), folder])
            console.print("\n[bold green]✅ Caption generation complete![/bold green]")
        except Exception as e:
            console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
        
        input("\nPress ENTER to continue...")
    
    def refresh_captions(self):
        """Run caption refresher"""
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold yellow]🔄 CAPTION REFRESHER[/bold yellow]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
        
        if not os.path.exists(self.csv_file):
            console.print(f"[bold red]❌ CSV file not found: {self.csv_file}[/bold red]")
            console.print("[yellow]Run 'Generate Captions' first![/yellow]")
            input("\nPress ENTER to continue...")
            return
        
        console.print("\n[dim]This will:[/dim]")
        console.print("[dim]  • Read existing CSV[/dim]")
        console.print("[dim]  • Generate fresh caption variations[/dim]")
        console.print("[dim]  • Create all-new hashtags[/dim]")
        console.print("[dim]  • Randomize order[/dim]")
        console.print("[dim]  • Save to new CSV[/dim]\n")
        
        if not Confirm.ask("[yellow]Ready to refresh captions?[/yellow]", default=True):
            return
        
        console.print("\n[bold green]🚀 Starting caption refresher...[/bold green]\n")
        
        try:
            subprocess.run([sys.executable, str(PROJECT_ROOT / "src" / "captions" / "refresher.py"), self.csv_file])
            console.print("\n[bold green]✅ Caption refresh complete![/bold green]")
        except Exception as e:
            console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
        
        input("\nPress ENTER to continue...")
    
    def upload_youtube(self):
        """Run YouTube uploader"""
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold yellow]📺 YOUTUBE UPLOADER[/bold yellow]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
        
        folder = self.get_video_folder()
        if not folder:
            return
        
        if not os.path.exists(self.csv_file):
            console.print(f"[bold red]❌ CSV file not found: {self.csv_file}[/bold red]")
            console.print("[yellow]Run 'Generate Captions' first![/yellow]")
            input("\nPress ENTER to continue...")
            return
        
        # Check for credentials
        config_dir = PROJECT_ROOT / "config"
        creds = list(config_dir.glob('client_secret*.json'))
        if not creds:
            console.print("[bold red]❌ OAuth credentials not found![/bold red]")
            console.print("[yellow]Please add your OAuth credentials JSON to config/[/yellow]")
            input("\nPress ENTER to continue...")
            return

        console.print(f"[green]✓ Found credentials: {creds[0].name}[/green]")
        console.print(f"[green]✓ Found CSV: {self.csv_file}[/green]")
        console.print(f"[green]✓ Video folder: {folder}[/green]\n")
        
        if not Confirm.ask("[yellow]Ready to upload to YouTube?[/yellow]", default=True):
            return
        
        console.print("\n[bold green]🚀 Starting YouTube uploader...[/bold green]\n")
        
        try:
            subprocess.run([sys.executable, str(PROJECT_ROOT / "src" / "uploaders" / "youtube.py"), folder])
            console.print("\n[bold green]✅ YouTube upload complete![/bold green]")
        except Exception as e:
            console.print(f"\n[bold red]❌ Error: {e}[/bold red]")

        input("\nPress ENTER to continue...")

    def upload_tiktok(self):
        """Run TikTok uploader"""
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold yellow]📱 TIKTOK UPLOADER[/bold yellow]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")

        folder = self.get_video_folder()
        if not folder:
            return

        if not os.path.exists(self.csv_file):
            console.print(f"[bold red]❌ CSV file not found: {self.csv_file}[/bold red]")
            console.print("[yellow]Run 'Generate Captions' first![/yellow]")
            input("\nPress ENTER to continue...")
            return

        console.print(f"[green]✓ Found CSV: {self.csv_file}[/green]")
        console.print(f"[green]✓ Video folder: {folder}[/green]\n")

        console.print("[dim]This will launch Chrome and automate TikTok Studio uploads.[/dim]")
        console.print("[dim]Your TikTok login is saved between sessions.[/dim]\n")

        if not Confirm.ask("[yellow]Ready to upload to TikTok?[/yellow]", default=True):
            return

        console.print("\n[bold green]🚀 Starting TikTok uploader...[/bold green]\n")

        try:
            subprocess.run([sys.executable, str(PROJECT_ROOT / "src" / "uploaders" / "tiktok.py"), folder])
            console.print("\n[bold green]✅ TikTok upload complete![/bold green]")
        except Exception as e:
            console.print(f"\n[bold red]❌ Error: {e}[/bold red]")

        input("\nPress ENTER to continue...")

    def upload_meta(self):
        """Run Meta (Instagram + Facebook) uploader"""
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold yellow]📸 META UPLOADER (Instagram + Facebook)[/bold yellow]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")

        folder = self.get_video_folder()
        if not folder:
            return

        if not os.path.exists(self.csv_file):
            console.print(f"[bold red]❌ CSV file not found: {self.csv_file}[/bold red]")
            console.print("[yellow]Run 'Generate Captions' first![/yellow]")
            input("\nPress ENTER to continue...")
            return

        # Check for meta config
        meta_config = PROJECT_ROOT / "config" / "meta_config.json"
        if not meta_config.exists():
            console.print("[bold red]❌ Meta config not found![/bold red]")
            console.print("[yellow]Create config/meta_config.json with your Meta API credentials.[/yellow]")
            console.print("[dim]See docs/SETUP.md for instructions.[/dim]")
            input("\nPress ENTER to continue...")
            return

        console.print(f"[green]✓ Found meta config[/green]")
        console.print(f"[green]✓ Found CSV: {self.csv_file}[/green]")
        console.print(f"[green]✓ Video folder: {folder}[/green]\n")

        if not Confirm.ask("[yellow]Ready to upload to Instagram & Facebook?[/yellow]", default=True):
            return

        console.print("\n[bold green]🚀 Starting Meta uploader...[/bold green]\n")

        try:
            subprocess.run([sys.executable, str(PROJECT_ROOT / "src" / "uploaders" / "meta.py"), folder])
            console.print("\n[bold green]✅ Meta upload complete![/bold green]")
        except Exception as e:
            console.print(f"\n[bold red]❌ Error: {e}[/bold red]")

        input("\nPress ENTER to continue...")
    
    def full_workflow(self):
        """Run complete workflow"""
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold yellow]🔧 FULL WORKFLOW[/bold yellow]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
        
        folder = self.get_video_folder()
        if not folder:
            return
        
        console.print("\n[bold]This workflow will:[/bold]")
        console.print("  1. [cyan]Generate captions from videos[/cyan]")
        console.print("  2. [cyan]Review CSV (you can edit)[/cyan]")
        console.print("  3. [cyan]Upload to YouTube[/cyan]\n")
        
        if not Confirm.ask("[yellow]Run full workflow?[/yellow]", default=True):
            return
        
        # Step 1: Generate
        console.print("\n[bold green]📍 Step 1/3: Generating captions...[/bold green]\n")
        try:
            subprocess.run([sys.executable, str(PROJECT_ROOT / "src" / "captions" / "generator.py"), folder])
        except Exception as e:
            console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
            input("\nPress ENTER to continue...")
            return
        
        # Step 2: Review
        console.print("\n[bold green]📍 Step 2/3: Review CSV[/bold green]")
        if Confirm.ask("[yellow]Open CSV for review/editing?[/yellow]", default=True):
            subprocess.run(["open", self.csv_file])
            input("\n[cyan]Edit the CSV if needed, then press ENTER to continue...[/cyan]")
        
        # Step 3: Upload
        console.print("\n[bold green]📍 Step 3/3: Uploading to YouTube...[/bold green]\n")
        try:
            subprocess.run([sys.executable, str(PROJECT_ROOT / "src" / "uploaders" / "youtube.py"), folder])
            console.print("\n[bold green]✅ Full workflow complete![/bold green]")
        except Exception as e:
            console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
        
        input("\nPress ENTER to continue...")
    
    def view_schedule(self):
        """View current video library and projected schedule"""
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold yellow]📊 VIDEO LIBRARY & PROJECTED SCHEDULE[/bold yellow]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")

        if not os.path.exists(self.csv_file):
            console.print(f"[bold red]❌ CSV file not found: {self.csv_file}[/bold red]")
            console.print("[yellow]Run 'Generate Captions' first![/yellow]")
            input("\nPress ENTER to continue...")
            return

        import csv
        import json
        from datetime import datetime, timedelta

        # Load posting schedule
        schedule_path = PROJECT_ROOT / "config" / "posting_schedule.json"
        with open(schedule_path, 'r') as f:
            schedule = json.load(f)

        # Read videos
        videos = []
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                videos.append(row)

        # Calculate projected dates
        current_date = datetime.now().date() + timedelta(days=1)
        table = Table(box=box.ROUNDED, border_style="cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Date", style="yellow")
        table.add_column("Day", style="cyan")
        table.add_column("Video", style="white", max_width=30)
        table.add_column("TT", style="magenta")
        table.add_column("YT", style="red")
        table.add_column("Meta", style="green")

        vid_idx = 0
        while vid_idx < len(videos):
            weekday_name = current_date.strftime('%A')
            if weekday_name in schedule:
                times = schedule[weekday_name]
                fname = videos[vid_idx]['filename']
                table.add_row(
                    str(vid_idx + 1),
                    current_date.strftime('%Y-%m-%d'),
                    weekday_name[:3],
                    fname[:27] + "..." if len(fname) > 30 else fname,
                    times['tiktok'],
                    times['youtube'],
                    times.get('meta', '-')
                )
                vid_idx += 1
            current_date += timedelta(days=1)

        console.print(table)
        console.print(f"\n[dim]Showing projected schedule if triggered tomorrow. {len(videos)} videos total.[/dim]")
        input("\nPress ENTER to continue...")
    
    def settings(self):
        """Settings menu"""
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold yellow]⚙️  SETTINGS[/bold yellow]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
        
        settings_table = Table(show_header=False, box=box.ROUNDED, border_style="cyan")
        settings_table.add_column("Setting", style="yellow")
        settings_table.add_column("Value", style="white")
        
        settings_table.add_row("Video Folder", self.video_folder or "[dim]Not set[/dim]")
        settings_table.add_row("CSV File", self.csv_file)
        settings_table.add_row("API Key Set", "✓" if os.environ.get('ANTHROPIC_API_KEY') else "✗")
        settings_table.add_row("YouTube Creds", "✓" if list((PROJECT_ROOT / "config").glob('client_secret*.json')) else "✗")
        settings_table.add_row("Meta Config", "✓" if (PROJECT_ROOT / "config" / "meta_config.json").exists() else "✗")
        
        console.print(settings_table)
        
        console.print("\n[bold]Options:[/bold]")
        console.print("  1. Change video folder")
        console.print("  2. Change CSV file")
        console.print("  3. Check API key")
        console.print("  0. Back to main menu\n")
        
        choice = Prompt.ask("[yellow]Select option[/yellow]", choices=["0", "1", "2", "3"], default="0")
        
        if choice == "1":
            self.video_folder = None
            self.get_video_folder()
        elif choice == "2":
            self.csv_file = Prompt.ask("[cyan]Enter CSV filename[/cyan]", default=self.csv_file)
        elif choice == "3":
            if os.environ.get('ANTHROPIC_API_KEY'):
                console.print("\n[green]✓ API key is set[/green]")
            else:
                console.print("\n[red]✗ API key not set[/red]")
                console.print("[yellow]Set it with:[/yellow] export ANTHROPIC_API_KEY='your-key'")
            input("\nPress ENTER to continue...")
    
    def run(self):
        """Main UI loop"""
        while True:
            console.clear()
            self.show_banner()
            
            choice = self.show_main_menu()
            
            if choice == "0":
                console.print("\n[bold cyan]👋 Thanks for using Golf Video Automation![/bold cyan]\n")
                break
            elif choice == "1":
                self.generate_captions()
            elif choice == "2":
                self.refresh_captions()
            elif choice == "3":
                self.upload_youtube()
            elif choice == "4":
                self.upload_tiktok()
            elif choice == "5":
                self.upload_meta()
            elif choice == "6":
                self.full_workflow()
            elif choice == "7":
                self.view_schedule()
            elif choice == "8":
                self.settings()


def main():
    ui = GolfAutomationUI()
    ui.run()


if __name__ == "__main__":
    main()
