# Quick Start: Create Your First Video

## Step 1: Generate Image Prompts
```bash
python make_video.py --topic "learn colors"
```
This opens Bing Image Creator with 12 ready-to-use prompts.

## Step 2: Create Images
1. Go to https://www.bing.com/create
2. Sign in with your Microsoft account
3. Copy each prompt from `output/prompts/prompts_learn_colors.txt`
4. Paste into Bing and click "Create"
5. Download the best image
6. Rename to `scene_01.png`, `scene_02.png`, etc.
7. Save all images to `input_images/` folder

## Step 3: Assemble Video
```bash
python make_video.py --topic "learn colors" --assemble
```

## Step 4: Find Your Video
Final video saved to: `output/videos/learn_colors_TIMESTAMP.mp4`

## Custom Narration (Optional)
Edit `sample_narration_colors.json` with your own narration text, then:
```bash
python make_video.py --topic "learn colors" --narration sample_narration_colors.json --assemble
```

## Tips
- Use descriptive filenames (`red_apple.png`, `blue_sky.png`)
- Images should be 1280x720 or larger
- Each image becomes an 8-second scene
- gTTS generates narration automatically
