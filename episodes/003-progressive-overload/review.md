# Review - 003-progressive-overload (JUDGE)

Checked: videos/003-progressive-overload.mp4 (ffprobe, 18 stills covering every scene including
0.0 s, 0.5 s and the last second, plus 3 stills from 001-skinny-fat.mp4 for comparison, plus
frame grids of every week-2/week-3 rep), script.json, gap_report.txt, ffmpeg silencedetect
(-35 dB, d=0.6), render.py.

Cut timeline (from gap_report): scene 1 0.00-2.58, scene 2 2.58-5.53, scene 3 5.53-9.04,
scene 4 9.04-11.80, scene 5 11.80-14.92.

## Checklist

- [PASS] Format: 1080x1920, 30 fps, h264 + one AAC voice track (mono voice on both channels),
  no music. 14.93 s.
- [PASS] Length 13-18 s: 14.93 s.
- [PASS] Hook text in first second: "SAME WEIGHT / FOR MONTHS?" pops in from frame 1 (fully
  visible by ~0.1 s, same as 001). Frame 0.0 is the pop-in start.
- [PASS] Text style: white with dark outline line 1, black on lime box line 2, large, bold,
  centered, y about 200-490 (inside 170-560 safe zone). Payoff "A LITTLE MORE / EVERY WEEK".
- [PASS after fix] Text never covers the head. Round 0: in scene 3 "WEEK 2 / +1 REP" the squat
  shot was framed so high that the mannequin's head sat behind the lime "+1 REP" box at the
  top of every rep (head top around y 320 vs box bottom around y 490). Fixed by framing the
  scene-3 squat lower and slightly wider. Week 1/4 bench and week 3 row checked frame by frame:
  head stays below/right of the text.
- [PASS] Mannequin consistency with 001: same gray featureless mannequin, dark shorts, same
  engine and same start physique (F0=1.0, M0=0.08). Side-by-side with 001 stills matches.
- [PASS] Believable physique / moderate change: weeks 1-4 change only slightly (f 1.00->0.88),
  payoff ends at f=0.30 m=0.55 (softer than 001's 0.16/0.72), light ab lines, natural shape.
- [PASS] Pacing: new visual every 1-3 s (bench w/ cobweb, calendar flip, squat, standing,
  week 1-4 lifts ~0.9 s each, barbell plate slide, log sheet, squat, payoff morph). Flash cuts
  and a page flip; no establishing shot.
- [PASS] Gym setting, clean lighting, slow push-ins/drifts.
- [PASS] No logos, brands, readable brand marks or real people (plates, bar, calendar and log
  sheet are blank or show only WEEK/+1).
- [PASS] No medical/supplement claims, no calorie or dosage prescriptions.
- [PASS] No body shaming: the start body is presented neutrally.
- [PASS] Humor slight: thin cobweb on the never-changing plates. Not cartoonish.
- [PASS] Food: none shown.
- [PASS] Voiceover: 5 lines, each with exactly one fuck/fucking. am_adam, speed 1.45.
- [PASS after fix] Caption: clean, 187 chars. Round 0 had hook + 3 sentences before the CTA
  ("That's why nothing changes." / "Log every lift..." / "Small jumps add up."). Merged the
  first into the hook so it is hook + 2 practical sentences + "Save this for your next gym day."
- [PASS] Hashtags: 7, topic-specific (#progressiveoverload, #trackyourlifts,
  #beginnerstrength, #liftingprogress), broad: #gymbeginner, #fitnesstips, #strengthgains (3).
  Not identical to 001's or 002's set.
- [PASS] tiktok_title: "Same weight for months? Add a little every week." 48 chars.
- [PASS] Plain ASCII in script.json, render.py, gap_report.txt and this file.
- [PASS] Gaps: silencedetect (-35 dB, 0.6 s) finds only the final text hold, 13.59-14.93 s
  (1.34 s). The only other pause (0.40 s at 11.40 s) is under 0.6 s.

## Changes

Round 1:
- render.py: lift_shot() gained a cyoff parameter (camera center shift). scene3 now frames the
  squat with zmul=0.9 and cyoff=210 so the head stays well below the "+1 REP" box for the whole
  rep. Other shots unchanged.
- script.json caption: "Lifting the same weight for months? That's why nothing changes. ..."
  -> "Lifting the same weight for months and nothing changes? ..." (hook + 2 + CTA).
- Re-rendered silent.mp4 (600 frames), reran tools/voice_and_cut.py (am_adam, 1.45) to remake
  videos/003-progressive-overload.mp4 and gap_report.txt. Re-checked: 14.93 s, 1080x1920 30 fps,
  same gaps, new stills (0.5 s, week-2 rep grid, 14.8 s) confirm the fix.

Round 2: not needed.

VERDICT: PASS
