# Review - 005-scale-alone (JUDGE)

Checked: videos/005-scale-alone.mp4 (ffprobe, ffmpeg silencedetect -40 dB d=0.6 and -50 dB d=0.3),
21 stills from the final mp4 (0.1, 0.5 s, every scene and sub-shot, last second 13.5 and 14.3 s),
4 extra transition frames (whip pans at 2.05 and 8.45 s, dissolve at 11.5 and 11.65 s),
2 stills from 001-skinny-fat.mp4 for mannequin comparison, script.json, gap_report.txt, render.py.
After the fix: re-rendered and re-checked 17 stills (including 3 frames through the dissolve),
plus probe and silencedetect.

Cut timeline (from gap_report): scene 1 0.00-2.07, scene 2 2.07-4.83, scene 3 4.83-8.44,
scene 4 8.44-11.45, scene 5 11.45-14.44.

## Checklist

- [PASS] Format: 1080x1920, 30 fps, h264 + one AAC voice track, no music (audio fully silent
  in the final hold). 14.43 s.
- [PASS] Length 13-18 s: 14.43 s.
- [PASS] Hook in first second: "SCALE NOT" from frame 1, "MOVING?" lime box by about 0.3 s,
  mannequin standing on a scale, then a top-down cut to the display. No establishing shot.
- [PASS] Text style: white with dark outline line 1, black on lime box line 2, large, bold,
  centered, about y 170-530 (inside 170-560). Payoff "NOT JUST / THE SCALE" held ~1.3 s.
- [PASS after fix] Text never covers the mannequin's head. In round 0, during the 0.3 s
  dissolve from scene 4 to scene 5 (about 11.45-11.75 s), scene 5's camera started framed
  high (cy 1300), so the incoming mannequin's head sat right behind the fading
  "THAT'S A / RECOMP" text. Fixed (see Changes); every other shot already kept the head clear.
- [PASS] Mannequin consistent with 001: same gray, smooth featureless mannequin, dark shorts,
  same engine, same skinny-fat start (F0=1.0, M0=0.08), same hands-on-hips pose.
- [PASS] Believable physique: the hands-on-hips shots at f=0.97 show a soft belly (the flanks
  are visible because the arms are out), consistent with how the engine draws skinny-fat, and
  not exaggerated. Moderate change: scene 4 f=0.64/m=0.36, payoff ends at F1=0.30/M1=0.55 (the
  same end state accepted in 003/004).
- [PASS] Scale reading "78.4" with no unit: a neutral body-weight display used to show that
  the number does not change. Not a calorie, dosage or target prescription. Acceptable.
- [PASS] No logos, brand names, readable marks or real people. Scale, plates and tape are plain.
- [PASS] No medical, supplement, calorie or dosage claims (VO, screen, caption). "Likely
  losing fat and building muscle" in the caption is hedged general fitness info.
- [PASS] No body shaming: the start body is shown neutrally, and the message is reassuring.
- [PASS] Humor: slight (rolling digits that always land on 78.4, frustrated hands on hips),
  not cartoonish.
- [PASS] Pacing: new visual every ~0.9-1.3 s in scenes 1-4 (whip pans at 2.07 and 8.44 s,
  flash cuts between sub-shots, a 0.3 s dissolve into scene 5). Payoff is one ~3 s shot with
  a slow push-out, light sweep and text pop, same as 001/003/004.
- [PASS] Voiceover: 5 lines, each with exactly one "fuck"/"fucking". am_adam, speed 1.45.
- [PASS] Caption: clean, 230 chars, hook + 2 practical sentences + "Save this for your next
  gym day."
- [PASS] Hashtags: 7. Broad: #gymbeginner, #fitnesstips (+ audience tag #skinnyfat). Topic:
  #nonscalevictory, #bodyrecomposition, #fitnessprogress, #recomp. Different set from 004.
- [PASS] tiktok_title: "Scale not moving? Check these 3 things." 39 chars.
- [PASS] Plain ASCII in script.json, render.py, gap_report.txt and this file (byte scan).
- [PASS] Gaps: the only silence over 0.6 s is the final text hold 13.09-14.43 s (1.35 s).
  Shorter pauses at scene changes are about 0.31 s.

## Changes

Round 1:
- render.py scene5: camera now starts at cy 1090 (was 1300) and eases to 1110, so the
  mannequin's head stays below the text zone through the dissolve. The slow push-out
  (zoom 1.2 to 1.06) and the light sweep are unchanged.
- Re-rendered silent.mp4 (600 frames, background nohup), then reran tools/voice_and_cut.py
  (am_adam, 1.45) to remake videos/005-scale-alone.mp4. gap_report.txt was rewritten from
  the tool's output. Timing unchanged: 14.43 s.
- script.json unchanged.

## Verdict

PASS
