# Review - 004-protein-every-meal (JUDGE)

Checked: videos/004-protein-every-meal.mp4 (ffprobe, ffmpeg silencedetect -40 dB d=0.6),
18 stills from the final mp4 (0.1, 0.5, 0.9 s, every scene and sub-shot, last second 15.0 and
15.45 s), extra frame-by-frame stills of the bench rep, 2 stills from 001-skinny-fat.mp4 for
mannequin comparison, script.json, gap_report.txt, render.py. After the fix: re-rendered and
re-checked 12 stills plus probe and silencedetect.

Cut timeline (from gap_report): scene 1 0.00-2.07, scene 2 2.07-5.11, scene 3 5.11-9.50,
scene 4 9.50-12.34, scene 5 12.34-15.53.

## Checklist

- [PASS] Format: 1080x1920, 30 fps, h264 + one AAC voice track, no music. 15.53 s.
- [PASS] Length 13-18 s: 15.53 s.
- [PASS] Hook in first second: "PROTEIN ONLY" from frame 1, "AT DINNER?" lime box by about
  0.2 s, mannequin eating toast with no protein on the table. No establishing shot.
- [PASS] Text style: white with dark outline line 1, black on lime box line 2, large, bold,
  centered, about y 170-500 (inside 170-560). Payoff "PROTEIN / EVERY MEAL" held ~1.4 s.
- [PASS] Text never covers the mannequin's head: eating shots, row, bench and payoff all keep
  the head well below the text.
- [PASS after fix] Text readability: in round 0 the bench plate rose into the bottom edge of the
  "LIFT HARD" lime box at the top of each rep. Fixed (see Changes); now a clear gap.
- [PASS] Mannequin consistency with 001: same gray, smooth featureless mannequin, dark shorts,
  same engine, same skinny-fat start physique.
- [PASS] Believable physique: start f=1.0/m=0.08, slight progress in scene 4 lifts, payoff ends
  at f=0.30 m=0.55 (same moderate end state accepted in 003), natural proportions.
- [PASS] Food not like a diet ad: plain home-style plates (toast and coffee, chips, a comically
  tall chicken pile, eggs, yogurt, chicken with rice, cottage cheese, salmon, beans). No
  packaging, labels or styled "meal prep" look. Humor (chicken mountain) is slight.
- [PASS] No logos, brand names, readable marks or real people. Mugs and bowls are plain.
- [PASS] No medical or supplement claims, no calorie, gram or dosage numbers (VO, screen,
  caption). No protein powder shown.
- [PASS] No body shaming; start body shown neutrally.
- [PASS] Pacing: new visual every ~1-1.4 s in scenes 1-4 (flash cuts, whip pans, slide-ins);
  payoff is one 3.2 s shot with push-out, light sweep and text pop, consistent with 001/003.
- [PASS] Voiceover: 5 lines, each with exactly one "fucking"/"fuck". am_adam, speed 1.45.
- [PASS] Caption: clean, 232 chars, hook + 2 practical sentences + "Save this for your next
  gym day."
- [PASS] Hashtags: 7. Broad: #gymbeginner, #fitnesstips (+ audience tag #skinnyfat). Topic:
  #highproteinmeals, #proteinateverymeal, #easymealideas, #musclebuildingtips. Different from
  003's set.
- [PASS] tiktok_title: "Only eating protein at dinner? Fix this." 40 chars.
- [PASS] Plain ASCII in script.json, render.py, gap_report.txt and this file.
- [PASS] Gaps: only silence is the final text hold 14.19-15.53 s (1.34 s).

## Changes

Round 1:
- render.py scene4: bench lift_shot now passes cyoff=115.0, framing the bench lower so the plate
  stays below the "LIFT HARD" box at lockout. Head position unaffected (still clear of text).
- Re-rendered silent.mp4 (600 frames, background nohup), reran tools/voice_and_cut.py
  (am_adam, 1.45) to remake videos/004-protein-every-meal.mp4 and gap_report.txt.
  Timing unchanged: 15.53 s.
- script.json unchanged.

## Verdict

PASS
