---
name: handdrawn-fashion-whiteboard
description: Use when the user provides a fashion sketch, apparel product image, clothing design image, or similar product illustration and asks for a hand-drawn whiteboard video, sketch drawing animation, 手绘视频, 笔迹动画, 白板动画, TikTok-ready music, or the last confirmed blue outfit video style.
---

# Handdrawn Fashion Whiteboard

Create a 10-second hand-drawn whiteboard MP4 from a user-provided fashion or product sketch, matching the approved blue outfit video style.

## Output Contract

Use these defaults unless the user explicitly changes them:

| Setting | Value |
|---|---|
| Duration | 10 seconds |
| FPS | 60 |
| Ink path | `skeleton` |
| Color fill | `contour-wipe` |
| Pause | `heavy` |
| Final clean display | about 0.5 seconds |
| Hand | realistic Western female hand |
| Pen | fine black technical pen |
| Color timing | color reveal is advanced by about 1 second |
| Hand after coloring | hide immediately once colored regions are complete |
| Color mask | color clothing/product regions only; do not recolor hair, face, skin, or ordinary line art |
| Music | original TikTok-style electronic bed, with at least 2 seconds of ending fadeout |

Preferred deliverable path is `D:\Codex输出`. If that write permission is not granted, save under the current task's `outputs\final` directory and tell the user.

## Workflow

1. Read `whiteboard-stream-animation` first; this skill builds on that renderer.
2. Use the user's supplied image directly. Do not regenerate the source image unless the user asks for a new source image.
3. Resolve paths relative to this `SKILL.md`:
   - Renderer: `scripts/render_handdrawn_fashion_whiteboard.py`
   - Hand asset: `assets/female-hand-black-technical-pen-soft-wrist.png`
   - Music helper: `scripts/add_tiktok_music.py`
4. Render a preview first when the user asks for a preview or is still iterating.
5. Render a final MP4 when the user confirms the preview.
6. If the user wants music, run the music helper on the final no-music MP4.
7. Verify the video opens, is 10.00 seconds, has 600 frames at 60fps, and inspect key frames around 7.5s, 8.0s, 8.5s, and 9.5s.

## Render Command

Use this shape, replacing paths as needed:

```powershell
& '<whiteboard-stream-animation-venv>\Scripts\python.exe' `
  '<this-skill>\scripts\render_handdrawn_fashion_whiteboard.py' `
  '<input-image>' `
  --out-dir '<output-dir>' `
  --total-ms 10000 `
  --gaze-seconds 0.5 `
  --ink-path skeleton `
  --color-fill contour-wipe `
  --pause heavy `
  --pen-image '<this-skill>\assets\female-hand-black-technical-pen-soft-wrist.png'
```

## Music Command

Use the music helper only after the visual MP4 is accepted:

```powershell
& '<whiteboard-stream-animation-venv>\Scripts\python.exe' `
  '<this-skill>\scripts\add_tiktok_music.py' `
  '<accepted-visual-mp4>' `
  --out '<final-with-music-mp4>' `
  --fade-start 8.0
```

## Visual Checks

Before returning the result:

- Confirm coloring begins on the garment/product, not on hair or head.
- Confirm hair, face, skin, gray sketch lines, and uncolored body regions stay unchanged during coloring.
- Confirm color appears close to the pen path and does not lag behind the hand.
- Confirm the hand disappears once color is complete, usually around 8 seconds for this 10-second style.
- Confirm the last portion is a clean finished image, not a hand moving over an already finished image.
- If music is present, confirm the last 2 seconds fade down naturally.
