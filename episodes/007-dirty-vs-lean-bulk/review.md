# Review - 007-dirty-vs-lean-bulk (JUDGE)

Checked: videos/007-dirty-vs-lean-bulk.mp4 (ffprobe, ffmpeg silencedetect -40 dB d=0.6 and
-50 dB d=0.3, volumedetect on the final hold), 19 stills from the final mp4 (0.03, 0.5, 0.9 s,
every scene and every sub-shot, payoff at 13.0/14.5/15.0 s, last second 15.4 s), 7 transition
frames (whip pans at 2.30/2.40 and 5.33/5.45 s, dissolve at 12.50/12.60 s, last frame 15.43 s),
2 stills from 001-skinny-fat.mp4 for mannequin comparison, script.json, gap_report.txt, render.py,
and render.py check mode over all 600 source frames (head vs text boxes).

Cut timeline (from gap_report): scene 1 0.00-2.36, scene 2 2.36-5.38, scene 3 5.38-9.49,
scene 4 9.49-12.44, scene 5 12.44-15.45.

## Checklist

- [PASS] Format: 1080x1920, 30/1 fps, h264 + one AAC voice track, no other streams.
- [PASS] No music: final hold is digital silence (mean and max -91.0 dB from 14.2 s).
- [PASS] Length 13-18 s: 15.47 s.
- [PASS] Hook in first second: "BULKING? / DON'T EAT LIKE THIS" fully on screen from frame 1
  (t=0.03), mannequin at a table of junk food with empty plates, eating at 0.9 s.
- [PASS] Text style and placement: white with dark outline line 1, black on lime box line 2,
  large, bold, centered, about y 200-520 (inside 170-560). Payoff "LEAN BULK / WINS." from 14.17 s.
- [PASS] Text never covers the mannequin's head: no overlap on any still; check mode over all 600
  frames reports 0 overlaps, minimum 53 px between head top and text bottom.
- [PASS] Mannequin consistent with 001: same gray, smooth featureless face, dark shorts, same
  engine, gym and skinny-fat start (F0=1.0, M0=0.08), compared side by side with 001 stills.
- [PASS] Believable physique, moderate change: dirty bulk adds a modest belly (f 1.14), lean bulk
  progresses gradually (f 0.97 -> 0.62) and ends at F1=0.42/M1=0.58, softer than the 0.30/0.55 end
  state accepted in 003-006. Nothing extreme.
- [PASS] No body shaming: "SOME MUSCLE / LOTS OF FAT" and "WAY LESS FAT GAIN" describe the method's
  outcome; the body is shown neutrally, no mocking.
- [PASS] Humor slight: "PLATE 11 / STILL GOING" plate stack, donut tower, cheese pull. Not cartoonish.
- [PASS] Food: the lean-bulk food is a normal plate plus pizza, eggs and yogurt on a wooden table,
  with "PIZZA SOMETIMES"; it does not read as a diet ad.
- [PASS] No logos, brand names or real people. Burger, fries cup, shake and pizza are generic, unmarked.
- [PASS] No medical or supplement claims, no calorie or dosage numbers in VO, on screen or caption
  ("small surplus" only; "PLATE 11" is a joke count, not a prescription). "Shakes" = milkshakes.
- [PASS] Voiceover: 5 lines, each with exactly one "fucking"; tools/voice_and_cut.py defaults
  am_adam, speed 1.45. Caption is clean.
- [PASS] Pacing: new visual every ~1.0-1.3 s in scenes 1-4, whip pans at 2.36 and 5.38 s, flash
  cuts between sub-shots, 0.23 s dissolve into scene 5. Payoff is one ~3 s shot with morph and
  text pop, same pattern as 001/003-006.
- [PASS] Gaps: the only silence over 0.6 s at -40 dB is the final hold 14.08-15.46 s (1.38 s).
  At -50 dB d=0.3 the only silence is the same final hold.
- [PASS] Caption: 225 chars, hook + practical sentence + "Save this for your next gym day."
- [PASS] Hashtags: 7. Broad: #gymbeginner, #fitnesstips (+ #bulking). Specific: #leanbulk,
  #dirtybulk, #musclegain, #skinnyfat. Different set from 006.
- [PASS] tiktok_title: "Bulking? Don't eat like this." 29 chars.
- [PASS] Plain ASCII in script.json, render.py, gap_report.txt and this file (byte scan).

Minor notes (not failures): the bench shot is a little hard to read at a glance (feet cut at the
left edge), and scene 5 has ~1.7 s without text before the payoff pops, as in earlier episodes.

## Changes

None. No fix rounds needed; render.py, script.json, silent.mp4 and the final mp4 are unchanged.

## Verdict

VERDICT: PASS
