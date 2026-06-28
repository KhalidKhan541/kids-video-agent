import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from src.config import settings
from src.agent.state import AgentState, VideoProject
from src.agent.graph import agent, create_initial_project
from src.tools.groq_tools import generate_script, generate_seo
from src.tools.image_tools import generate_batch, generate_thumbnail
from src.tools.piper_tts_tools import generate_narration_segments
from src.tools.music_tools import get_kids_bgm
from src.tools.ffmpeg_tools import compose_final

console = Console()

RHYMES = {
    "twinkle_twinkle": {"title": "Twinkle Twinkle Little Star", "topic": "stars and night sky"},
    "old_mcdonald": {"title": "Old MacDonald Had a Farm", "topic": "farm animals"},
    "itsy_bitsy_spider": {"title": "Itsy Bitsy Spider", "topic": "spider adventure"},
    "mary_had_a_little_lamb": {"title": "Mary Had a Little Lamb", "topic": "farm animals and friendship"},
    "jack_and_jill": {"title": "Jack and Jill", "topic": "hill adventure"},
    "humpty_dumpty": {"title": "Humpty Dumpty", "topic": "egg on the wall"},
    "baa_baa_black_sheep": {"title": "Baa Baa Black Sheep", "topic": "sheep and wool"},
    "row_row_row_your_boat": {"title": "Row Row Row Your Boat", "topic": "boat on the river"},
    "johnny_johnny": {"title": "Johnny Johnny Yes Papa", "topic": "family fun"},
    "five_little_ducks": {"title": "Five Little Ducks", "topic": "ducklings adventure"},
    "wheels_on_the_bus": {"title": "The Wheels on the Bus", "topic": "bus ride"},
    "if_youre_happy": {"title": "If You're Happy and You Know It", "topic": "feelings and emotions"},
    "baby_shark": {"title": "Baby Shark", "topic": "ocean animals"},
    "patty_cake": {"title": "Pat-a-Cake", "topic": "baking fun"},
    "rain_rain_go_away": {"title": "Rain Rain Go Away", "topic": "weather and rain"},
}


@click.group()
@click.version_option(version="1.0.0", prog_name="kids-video-agent")
def cli():
    """Kids Video Agent - AI-powered nursery rhyme video generator"""
    pass


@cli.command()
@click.argument("title")
@click.option("--topic", "-t", help="Topic or theme for the video", default=None)
@click.option("--scenes", "-s", type=int, help="Number of scenes", default=5)
@click.option("--style", help="Art style (e.g., watercolor, cartoon, pixel)", default="cartoon")
@click.option("--output", "-o", help="Output directory", default=None)
@click.option("--with-music", is_flag=True, help="Add background music")
@click.option("--resolution", help="Video resolution (720p, 1080p)", default="1080p")
def create(title, topic, scenes, style, output, with_music, resolution):
    """Create a single video from start to finish"""
    console.print(Panel(f"[bold cyan]Creating video: {title}[/bold cyan]", border_style="cyan"))

    project = create_initial_project(title=title, topic=topic or title, num_scenes=scenes)

    output_dir = Path(output) if output else Path("output") / title.lower().replace(" ", "_")
    output_dir.mkdir(parents=True, exist_ok=True)

    state = AgentState(
        project=project,
        output_dir=str(output_dir),
        style=style,
        with_music=with_music,
        resolution=resolution,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running pipeline...", total=None)

        result = agent.invoke(state)

        progress.update(task, description="Pipeline complete!")

    console.print(Panel(f"[bold green]Video created successfully![/bold green]", border_style="green"))
    console.print(f"Output: {output_dir}")


@cli.command("generate-video")
@click.argument("title")
@click.option("--topic", "-t", help="Topic or theme for the video", default=None)
@click.option("--scenes", "-s", type=int, help="Number of scenes", default=5)
@click.option("--style", help="Art style", default="cartoon")
@click.option("--output", "-o", help="Output directory", default=None)
@click.option("--with-music", is_flag=True, help="Add background music")
@click.option("--resolution", help="Video resolution (720p, 1080p)", default="1080p")
def generate_video(title, topic, scenes, style, output, with_music, resolution):
    """Full pipeline: Groq -> Pollinations -> Piper -> Pixabay -> FFmpeg"""
    console.print(Panel("[bold magenta]Full Pipeline Generation[/bold magenta]", border_style="magenta"))
    console.print(f"Title: {title}")
    console.print(f"Topic: {topic or title}")
    console.print(f"Scenes: {scenes}")
    console.print(f"Style: {style}")
    console.print(f"Resolution: {resolution}")

    output_dir = Path(output) if output else Path("output") / title.lower().replace(" ", "_")
    output_dir.mkdir(parents=True, exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Step 1: Generating script with Groq...", total=4)
        script_data = generate_script(title=title, topic=topic or title, num_scenes=scenes)
        progress.update(task, advance=1, description="Step 2: Generating scene images with Pollinations...")

        scene_images = generate_scene_images(scenes_data=script_data["scenes"], style=style, output_dir=str(output_dir))
        progress.update(task, advance=1, description="Step 3: Synthesizing speech with Piper TTS...")

        audio_data = synthesize_scenes(scenes_data=script_data["scenes"], output_dir=str(output_dir))
        progress.update(task, advance=1, description="Step 4: Composing video with FFmpeg...")

        video_path = compose_video(
            title=title,
            scenes=script_data["scenes"],
            scene_images=scene_images,
            audio_data=audio_data,
            output_dir=str(output_dir),
            resolution=resolution,
        )
        progress.update(task, advance=1, description="Done!")

    if with_music:
        console.print("Downloading background music...")
        music = search_and_download_music(query=f"kids nursery rhyme instrumental {topic or title}", output_dir=str(output_dir))

    seo = generate_seo_metadata(title=title, topic=topic or title, scenes=script_data["scenes"])

    console.print(Panel(f"[bold green]Video generated successfully![/bold green]", border_style="green"))
    console.print(f"Video: {video_path}")
    console.print(f"Title: {seo['title']}")
    console.print(f"Description: {seo['description'][:100]}...")
    console.print(f"Tags: {', '.join(seo['tags'][:5])}")


@cli.command("batch")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--output", "-o", help="Output directory", default="output")
@click.option("--style", help="Art style", default="cartoon")
@click.option("--with-music", is_flag=True, help="Add background music")
@click.option("--resolution", help="Video resolution (720p, 1080p)", default="1080p")
def batch(input_file, output, style, with_music, resolution):
    """Process multiple videos from JSON"""
    with open(input_file, "r") as f:
        videos = json.load(f)

    console.print(Panel(f"[bold cyan]Batch processing {len(videos)} videos[/bold cyan]", border_style="cyan"))

    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, video_config in enumerate(videos, 1):
        title = video_config.get("title", f"Video {i}")
        topic = video_config.get("topic", title)
        num_scenes = video_config.get("scenes", 5)

        console.print(f"\n[bold]Processing {i}/{len(videos)}: {title}[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Creating {title}...", total=None)

            project = create_initial_project(title=title, topic=topic, num_scenes=num_scenes)
            video_output = output_dir / title.lower().replace(" ", "_")
            video_output.mkdir(parents=True, exist_ok=True)

            state = AgentState(
                project=project,
                output_dir=str(video_output),
                style=style,
                with_music=with_music,
                resolution=resolution,
            )

            result = agent.invoke(state)
            results.append({"title": title, "status": "success", "output": str(video_output)})

            progress.update(task, description=f"Completed {title}")

    console.print(Panel(f"[bold green]Batch processing complete![/bold green]", border_style="green"))

    table = Table(title="Batch Results", box=box.ROUNDED)
    table.add_column("Title", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Output")
    for r in results:
        table.add_row(r["title"], r["status"], r["output"])
    console.print(table)


@cli.command("list-rhymes")
@click.option("--topic", "-t", help="Filter by topic keyword", default=None)
def list_rhymes(topic):
    """List built-in nursery rhymes"""
    console.print(Panel("[bold cyan]Built-in Nursery Rhymes[/bold cyan]", border_style="cyan"))

    table = Table(title="Available Rhymes", box=box.ROUNDED)
    table.add_column("Key", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Topic", style="yellow")

    filtered = RHYMES
    if topic:
        filtered = {k: v for k, v in RHYMES.items() if topic.lower() in v["topic"].lower()}

    for key, info in filtered.items():
        table.add_row(key, info["title"], info["topic"])

    console.print(table)
    console.print(f"\n[bold]{len(filtered)}[/bold] rhymes found")


@cli.command("search")
@click.argument("query")
@click.option("--topic", "-t", help="Filter by topic keyword", default=None)
def search(query, topic):
    """Search rhymes by keyword"""
    console.print(Panel(f"[bold cyan]Search: {query}[/bold cyan]", border_style="cyan"))

    results = {}
    query_lower = query.lower()
    for key, info in RHYMES.items():
        if query_lower in info["title"].lower() or query_lower in info["topic"].lower() or query_lower in key:
            results[key] = info

    if topic:
        results = {k: v for k, v in results.items() if topic.lower() in v["topic"].lower()}

    table = Table(title="Search Results", box=box.ROUNDED)
    table.add_column("Key", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Topic", style="yellow")

    for key, info in results.items():
        table.add_row(key, info["title"], info["topic"])

    console.print(table)
    console.print(f"\n[bold]{len(results)}[/bold] results found")


@cli.command("status")
def status():
    """Show config"""
    console.print(Panel("[bold cyan]Configuration[/bold cyan]", border_style="cyan"))

    table = Table(title="Settings", box=box.ROUNDED)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("GROQ_API_KEY", "Set" if settings.groq_api_key else "Not set")
    table.add_row("POLLINATIONS_API_KEY", "Set" if settings.pollinations_api_key else "Not set")
    table.add_row("PIPER_MODEL", settings.piper_model if hasattr(settings, 'piper_model') else "Default")
    table.add_row("PIXABAY_API_KEY", "Set" if settings.pixabay_api_key else "Not set")
    table.add_row("OUTPUT_DIR", str(settings.output_dir) if hasattr(settings, 'output_dir') else "output")
    table.add_row("RESOLUTION", str(settings.resolution) if hasattr(settings, 'resolution') else "1080p")

    console.print(table)


@cli.command("queue")
@click.option("--action", "-a", type=click.Choice(["add", "list", "remove", "clear"]), help="Queue action", default="list")
@click.option("--title", help="Video title for add action")
@click.option("--topic", help="Video topic for add action")
@click.option("--index", type=int, help="Queue index for remove action")
def queue(action, title, topic, index):
    """Manage upload queue"""
    queue_file = Path("upload_queue.json")

    if queue_file.exists():
        with open(queue_file, "r") as f:
            queue_data = json.load(f)
    else:
        queue_data = {"pending": [], "completed": []}

    if action == "add":
        if not title:
            console.print("[bold red]Title is required for add action[/bold red]")
            return
        queue_data["pending"].append({
            "title": title,
            "topic": topic or title,
            "added_at": datetime.now().isoformat(),
        })
        with open(queue_file, "w") as f:
            json.dump(queue_data, f, indent=2)
        console.print(f"[bold green]Added '{title}' to queue[/bold green]")

    elif action == "list":
        console.print(Panel("[bold cyan]Upload Queue[/bold cyan]", border_style="cyan"))
        table = Table(title="Pending Uploads", box=box.ROUNDED)
        table.add_column("#", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Topic", style="yellow")
        table.add_column("Added At")
        for i, item in enumerate(queue_data["pending"]):
            table.add_row(str(i + 1), item["title"], item["topic"], item.get("added_at", "N/A"))
        console.print(table)

    elif action == "remove":
        if index is None or index < 1 or index > len(queue_data["pending"]):
            console.print("[bold red]Invalid index[/bold red]")
            return
        removed = queue_data["pending"].pop(index - 1)
        with open(queue_file, "w") as f:
            json.dump(queue_data, f, indent=2)
        console.print(f"[bold green]Removed '{removed['title']}' from queue[/bold green]")

    elif action == "clear":
        queue_data["pending"] = []
        with open(queue_file, "w") as f:
            json.dump(queue_data, f, indent=2)
        console.print("[bold green]Queue cleared[/bold green]")


@cli.command("schedule")
@click.option("--days", "-d", type=int, help="Number of days to schedule", default=7)
@click.option("--videos-per-day", "-v", type=int, help="Videos per day", default=2)
def schedule(days, videos_per_day):
    """Generate content calendar"""
    console.print(Panel("[bold cyan]Content Calendar[/bold cyan]", border_style="cyan"))

    table = Table(title=f"Schedule for {days} days ({videos_per_day} videos/day)", box=box.ROUNDED)
    table.add_column("Date", style="cyan")
    table.add_column("Video 1", style="green")
    table.add_column("Video 2", style="yellow")

    rhyme_keys = list(RHYMES.keys())
    today = datetime.now()

    for day in range(days):
        date = today + timedelta(days=day)
        date_str = date.strftime("%Y-%m-%d")
        v1 = RHYMES[rhyme_keys[day % len(rhyme_keys)]]
        v2 = RHYMES[rhyme_keys[(day + len(rhyme_keys) // 2) % len(rhyme_keys)]]
        table.add_row(date_str, v1["title"], v2["title"])

    console.print(table)
    console.print(f"\n[bold]{days * videos_per_day}[/bold] videos scheduled")


@cli.command("suggest")
@click.option("--topic", "-t", help="Filter suggestions by topic", default=None)
@click.option("--count", "-c", type=int, help="Number of suggestions", default=5)
def suggest(topic, count):
    """Show trending suggestions"""
    console.print(Panel("[bold cyan]Trending Suggestions[/bold cyan]", border_style="cyan"))

    trending_topics = [
        {"topic": "animals", "trend_score": 95, "reason": "Always popular with toddlers"},
        {"topic": "space", "trend_score": 88, "reason": "Curiosity about planets"},
        {"topic": "feelings", "trend_score": 85, "reason": "Social-emotional learning trend"},
        {"topic": "dinosaurs", "trend_score": 82, "reason": "Evergreen interest"},
        {"topic": "colors", "trend_score": 80, "reason": "Fundamental learning"},
        {"topic": "numbers", "trend_score": 78, "reason": "Educational content demand"},
        {"topic": "vehicles", "trend_score": 75, "reason": "Transportation fascination"},
        {"topic": "nature", "trend_score": 72, "reason": "Outdoor exploration"},
        {"topic": "music", "trend_score": 70, "reason": "Musical learning"},
        {"topic": "cooking", "trend_score": 68, "reason": "Fun food education"},
    ]

    if topic:
        trending_topics = [t for t in trending_topics if topic.lower() in t["topic"]]

    trending_topics.sort(key=lambda x: x["trend_score"], reverse=True)
    trending_topics = trending_topics[:count]

    table = Table(title="Trending Topics", box=box.ROUNDED)
    table.add_column("Topic", style="cyan")
    table.add_column("Score", style="green")
    table.add_column("Reason", style="yellow")

    for t in trending_topics:
        table.add_row(t["topic"], str(t["trend_score"]), t["reason"])

    console.print(table)

    console.print("\n[bold]Suggested Videos:[/bold]")
    for i, t in enumerate(trending_topics, 1):
        console.print(f"  {i}. {t['topic'].title()} Adventure - {t['reason']}")


if __name__ == "__main__":
    cli()
