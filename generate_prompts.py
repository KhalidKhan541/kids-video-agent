import os
import json
from datetime import datetime

# Generate prompts for Animal Dance Party
prompts = [
    "Scene 1: A cute pink cow with big sparkling eyes dancing in a colorful meadow, 3D cartoon style, Pixar-inspired, vibrant colors, soft lighting, detailed background with flowers and butterflies, 8K render quality",
    "Scene 2: A happy penguin wearing a tiny top hat doing a silly dance on ice, 3D cartoon style, subsurface scattering, volumetric lighting, adorable expression, snowflakes falling, 8K render quality",
    "Scene 3: A fluffy white bunny hopping and twirling with joy in a magical garden, 3D cartoon style, soft warm lighting, detailed fur texture, rainbow in background, 8K render quality",
    "Scene 4: A friendly lion cub doing a playful dance with its mane flowing, 3D cartoon style, Pixar-inspired, golden hour lighting, expressive eyes, savanna background, 8K render quality",
    "Scene 5: All animals together in a circle doing a happy dance under colorful balloons, 3D cartoon style, vibrant celebration scene, confetti, party atmosphere, 8K render quality"
]

# Save prompts
output_dir = r"C:\Users\khali\kids-video-agent\output\prompts"
os.makedirs(output_dir, exist_ok=True)

prompts_file = os.path.join(output_dir, "animal_dance_party.txt")
with open(prompts_file, "w") as f:
    f.write("ANIMAL DANCE PARTY - Bing Image Creator Prompts\n")
    f.write("=" * 50 + "\n\n")
    for i, prompt in enumerate(prompts, 1):
        f.write(f"Scene {i}: {prompt}\n\n")

# Also create a JSON version
json_file = os.path.join(output_dir, "animal_dance_party.json")
data = {
    "topic": "animal dance party",
    "numScenes": 5,
    "prompts": [{"scene": i+1, "prompt": p} for i, p in enumerate(prompts)],
    "createdAt": datetime.now().isoformat()
}
with open(json_file, "w") as f:
    json.dump(data, f, indent=2)

print(f"Prompts saved to: {prompts_file}")
print(f"JSON saved to: {json_file}")
print(f"\nCreated {len(prompts)} prompts for Animal Dance Party")
