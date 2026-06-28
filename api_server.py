#!/usr/bin/env python3
"""API server for n8n - generates images + runs video pipeline."""
import json, subprocess, webbrowser, os, sys, urllib.request, time, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

KIDS_DIR = r"C:\Users\khali\kids-video-agent"
INPUT_DIR = os.path.join(KIDS_DIR, "input_images")
PROMPTS_DIR = os.path.join(KIDS_DIR, "output", "prompts")

PROMPTS = [
    "Colorful elephant painting with a brush, 3D cartoon, Pixar style, 8K",
    "Playful monkey swinging on vines, 3D cartoon, Pixar style, 8K",
    "Cheerful giraffe eating leaves, 3D cartoon, Pixar style, 8K",
    "Joyful zebra doing a twirl, 3D cartoon, Pixar style, 8K",
    "All jungle friends having a parade, 3D cartoon, Pixar style, 8K",
]

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{}"

def download_images():
    os.makedirs(INPUT_DIR, exist_ok=True)
    results = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for i, prompt in enumerate(PROMPTS, 1):
        url = POLLINATIONS_URL.format(urllib.parse.quote(prompt))
        filename = f"scene_{i:02d}.jpg"
        filepath = os.path.join(INPUT_DIR, filename)
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                with open(filepath, "wb") as f:
                    f.write(resp.read())
            size = os.path.getsize(filepath)
            results.append({"scene": i, "file": filename, "size": size})
            print(f"  OK: {filename} ({size} bytes)")
            if i < 5:
                time.sleep(20)  # Wait 20s between requests to avoid rate limit
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"  Rate limited on scene {i}, waiting 60s...")
                time.sleep(60)
                # Retry once
                try:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        with open(filepath, "wb") as f:
                            f.write(resp.read())
                    size = os.path.getsize(filepath)
                    results.append({"scene": i, "file": filename, "size": size})
                    continue
                except Exception as e2:
                    results.append({"scene": i, "file": filename, "error": f"Retry failed: {e2}"})
            else:
                results.append({"scene": i, "file": filename, "error": str(e)})
        except Exception as e:
            results.append({"scene": i, "file": filename, "error": str(e)})
    return results

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == "/generate-images":
                r = download_images()
                self._ok({"images": r})
            elif self.path == "/open-bing":
                webbrowser.open("https://www.bing.com/create")
                self._ok({"message": "Bing opened"})
            elif self.path == "/run-pipeline":
                topic = "animal dance party"
                r = subprocess.run(
                    ["python", os.path.join(KIDS_DIR, "make_video.py"),
                     "--topic", topic, "--assemble"],
                    cwd=KIDS_DIR, capture_output=True, text=True, timeout=300)
                video_path = os.path.join(KIDS_DIR, "output", "videos", topic.replace(' ', '_') + ".mp4")
                self._ok({"success": r.returncode == 0,
                          "output": r.stdout[-500:] if r.stdout else "",
                          "video_path": video_path})
            elif self.path == "/health":
                self._ok({"status": "ok"})
            else:
                self.send_error(404)
        except Exception as e:
            self._err(str(e))

    def _ok(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _err(self, msg):
        self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": msg}).encode())

    def log_message(self, *a): pass

if __name__ == "__main__":
    port = 8787
    print(f"API on http://127.0.0.1:{port}")
    print(f"  GET /generate-images  - Generates 5 AI images via Pollinations.ai")
    print(f"  GET /run-pipeline     - Runs video pipeline")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
