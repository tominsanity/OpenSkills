---
name: activity-poster-psd
description: Generate high-resolution Chinese community activity posters from a fixed PSD template by replacing three activity entries. Use when Codex receives activity poster content with dates, tags, categories, titles, hosts, times, and venues, especially for the Hangzhou Gongshu Shangtang Cai Ma future community weekly activity poster PSD workflow.
---

# Activity Poster PSD

## Workflow

Use this skill to replace three activity entries in the PSD poster template and export a high-resolution PNG.

1. Parse the user-provided activity text into exactly three event objects.
2. Normalize fields:
   - `tag`: use an empty string for `无`, `无标签`, `none`, or blank.
   - `place`: split compact venues such as `蔡马邻里`, `蔡马青隅`, `蔡马童筑` into two lines: `蔡马\n邻里`.
   - Keep the user’s stated weekday unless it conflicts with an obvious same-date inconsistency; mention any correction in the final response.
   - For date ranges, keep compact text such as `08/14-08/16` and weekday ranges such as `周五-周日`.
3. Create an events JSON file matching `references/event-format.json`.
4. Run `scripts/render_activity_poster.py`.
5. Inspect the rendered image before responding. Confirm:
   - Titles stay on one line and do not overlap the category, divider dots, host, or card borders.
   - The divider dots are a single row only.
   - Tags do not cover dates.
   - Date ranges fit naturally in the left date card.
   - Output is `2048 x 3072`, `300 DPI`.

## Rendering Rules

- Use the PSD layer structure whenever available. Render a blank template by excluding original editable activity text layers, then draw new text transparently over the PSD background.
- Keep the numbered badges `01`, `02`, and `03`.
- Rebuild only the interior of the left date cards because the original date text may be merged into the background.
- Do not use opaque white rectangles behind activity text. Preserve the PSD paper texture.
- Keep the main title on one line. Reduce font size as needed instead of wrapping.
- Keep category and title separated. Leave enough vertical space so no text touches.
- Keep the dotted divider as one row. Prefer the native PSD divider if present; do not draw an additional row unless the blank template lacks it.
- Keep all three event cards visually consistent.

## Script

Use:

```powershell
python scripts/render_activity_poster.py `
  --template "D:\mydoc\yanzi\空间活动发布海报模板.psd" `
  --events events.json `
  --output "C:\Users\admin\Documents\PSD\空间活动发布海报_高清.png"
```

If `psd_tools` is unavailable, install it into a local dependency folder or use the bundled runtime Python. Do not globally modify the user’s Python environment unless explicitly asked.

## Input Format

Read [references/event-format.json](references/event-format.json) when constructing or validating the events JSON.
