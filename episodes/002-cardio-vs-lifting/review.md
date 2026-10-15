# Review - 002-cardio-vs-lifting (JUDGE)

Checked: videos/002-cardio-vs-lifting.mp4 (ffprobe, 12 stills from every scene including
0.0 s, 0.5 s and the last second, plus 3 stills from 001-skinny-fat.mp4 for comparison),
script.json, gap_report.txt, ffmpeg silencedetect (-35 dB, d=0.6), render.py.

## Checklist

- [PASS] Format: 1080x1920, 30 fps, h264 + one AAC voice track, no music. 14.77 s.
- [PASS] Length 13-18 s: 14.77 s.
- [PASS] Hook text in first second: "ENDLESS CARDIO? / STILL SKINNY-FAT?" pops in from frame 1
  (fully visible by 0.1 s, as in 001). Frame 0.0 is the pop-in start.
- [PASS] Text style: white with dark outline line 1, black on lime box line 2, large and bold,
  centered, y about 200-470 (inside 170-560 safe zone).
- [PASS] Text never covers the head: head is below the text in hook and payoff frames.
- [PASS after fix] Mannequin consistency with 001: same gray featureless mannequin, dark shorts,
  same engine. Round 0 issue: the scene 2 "same body" shot used hands-on-hips, which revealed
  the f=1.0 belly contour and read as an overweight pot belly, not skinny-fat, and looked
  inconsistent with the treadmill shot and 001's skinny-fat look. Fixed (arms down).
- [PASS] Believable physique / moderate change: end physique f=0.28 m=0.58 (softer than 001's
  end), light ab lines, natural proportions.
- [PASS] Pacing: new visual every 1-3 s (treadmill, sweaty close-up, wall clock, standing,
  squat/bench/row/press ~0.9 s each, walk, protein plate, payoff morph). Whip pans, flash cuts
  and a dissolve into the payoff. No establishing shot.
- [PASS] Gym setting, clean lighting, slow push-ins/drifts.
- [PASS] No logos, brands, or real people (treadmill console is blank).
- [PASS] No medical/supplement claims, no calorie or dosage prescriptions.
- [PASS] No body shaming (after fix the "before" body is plain skinny-fat, presented neutrally).
- [PASS] Humor slight: sweat drops and a small sweat puddle, spinning wall clock. Not cartoonish.
- [PASS] Food: plain chicken, rice, broccoli, eggs on a wooden table. Not a diet ad.
- [PASS] Voiceover: 5 lines, each with one fuck/fucking. am_adam, speed 1.45.
- [PASS] Caption: clean, hook + practical sentences + "Save this for your next gym day."
  191 chars.
- [PASS after edit] Hashtags: 7, topic-specific. Originally had 4 broad tags (#gymbeginner,
  #fitnesstips, #strengthtraining, #fatlossjourney); swapped #fatlossjourney for
  #beginnerlifting to get 3 broad. Not identical to 001's set.
- [PASS] tiktok_title: "Endless cardio? Still skinny-fat? Lift first." 45 chars.
- [PASS] Plain ASCII in script.json and render.py.
- [PASS] Gaps: only silence is the final text hold, 13.39-14.76 s (1.36 s). No other silence
  over 0.6 s.

## Changes

Round 1:
- render.py scene2 standing shot: figure_front(..., hips=1.0, ...) -> hips=0.0 (arms down,
  matching 001's skinny-fat pose), so the "still the same body" shot reads as skinny-fat.
- script.json hashtags: #fatlossjourney -> #beginnerlifting (2-3 broad rule).
- Re-rendered silent.mp4 (600 frames), reran tools/voice_and_cut.py (am_adam, 1.45) to remake
  videos/002-cardio-vs-lifting.mp4 and gap_report.txt. Re-checked: 14.77 s, 1080x1920 30 fps,
  same gaps, new stills confirm the fix.

Round 2: not needed.

VERDICT: PASS
