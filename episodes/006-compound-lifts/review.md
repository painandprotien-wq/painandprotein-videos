# Review - 006-compound-lifts (JUDGE)

Checked: videos/006-compound-lifts.mp4 (ffprobe, ffmpeg silencedetect -40 dB d=0.6 and -50 dB d=0.3,
volumedetect on the final hold), 35 stills from the final mp4 (0.03, 0.1, 0.5 s, every scene and
sub-shot, every on-screen text change, last second 15.4 and 16.3 s), transition frames (whip pans at
2.3/2.4/2.5 and 5.5/5.6 s, dissolve at 12.8/12.9/13.0 s), 3 full-resolution crops of the flagged
props, 2 stills from 001-skinny-fat.mp4 for mannequin comparison, script.json, gap_report.txt,
render.py. Run with the owner override for this run: exactly 8 hashtags.
After the fix: 11 render.py test stills of the changed shots, render.py check mode over all 600
frames, then 14 stills from the new final mp4 (hook, whip, wrist curl x2, deadlift, press x2,
rack x4, dissolve, payoff, last frame), plus probe and silencedetect.

Cut timeline (from gap_report): scene 1 0.00-2.41, scene 2 2.41-5.55, scene 3 5.55-9.20,
scene 4 9.20-12.76, scene 5 12.76-16.36.

## Checklist

- [PASS] Format: 1080x1920, 30 fps, h264 + one AAC voice track. No music: the final hold is
  digital silence (mean -91 dB, max -69.5 dB). 16.37 s.
- [PASS] Length 13-18 s: 16.37 s.
- [PASS] Hook in first second: "NEW TO LIFTING? / STOP DOING THIS" fully on screen from frame 1,
  skinny-fat mannequin doing tiny lateral raises with tiny dumbbells, punch-in at 1.2 s.
- [PASS] Text style: white with dark outline line 1, black on lime box line 2, large, bold,
  centered, about y 190-525 (inside 170-560). Payoff "COMPOUNDS / FIRST." from 14.8 s, held ~1.5 s.
- [PASS] Text never covers the mannequin's head: checked on every still and with render.py check
  mode over all 600 source frames (0 overlaps, minimum 48 px between head top and text bottom),
  including both sides of the 12.76-13.03 s dissolve and the whip pans.
- [PASS] Mannequin consistent with 001: same gray, smooth featureless mannequin, dark shorts, same
  engine and gym, same skinny-fat start (F0=1.0, M0=0.08). The soft belly shows more in the hook
  because the arms are out (same engine shape accepted in 005).
- [PASS] Believable physique, moderate change: scenes 1-2 stay skinny-fat ("same body"), the lifts
  show gradual progress (f 0.95 to 0.78), lockout f=0.68, payoff ends at F1=0.30/M1=0.55, the same
  end state accepted in 003/004/005.
- [PASS after fix] Close-up props readable. Round 0: the wrist-curl forearm was an untapered,
  over-long capsule with no elbow (read as a gray rod); the rack shot arm was a bat-like capsule
  ending in a ball that hid the small dumbbell; the lime "muscle glow" on the press read as
  green-tinted skin and a smudge drawn over the plate. Fixed (see Changes). Now the wrist curl shows
  upper arm, elbow, tapered forearm and hand with the dumbbell; the rack shot shows elbow, forearm
  and a hand gripping the small dumbbell, which then stays visible on the rack.
- [PASS] No logos, brand names, readable marks or real people. Plates, rack and cable are plain.
- [PASS] No medical, supplement, calorie or dosage claims (VO, screen, caption). "SET 19 / SET 31"
  is the joke about endless sets, not a prescription.
- [PASS] No body shaming: "MONTHS LATER / SAME BODY" is about the method, the body is shown
  neutrally.
- [PASS] Humor: slight (set 19 kickbacks, set 31 wrist curls, the tiny dumbbell back on the rack),
  not cartoonish.
- [PASS] Pacing: new visual every ~0.9-1.3 s in scenes 1-4 (whip pans at 2.41 and 5.55 s, flash
  cuts between sub-shots, 0.27 s dissolve into scene 5). Payoff is one ~3.6 s shot with a
  continuous recomp morph, light sweep and text pop at 14.8 s, same pattern as 001/003-005.
- [PASS] Voiceover: 5 lines, each with exactly one "fucking". am_adam, speed 1.45.
- [PASS] Caption: clean, 229 chars, hook + practical sentence + "Save this for your next gym day."
- [PASS] Hashtags: exactly 8 (owner override). Broad: #gymbeginner, #gymtok, #fitnesstips.
  Topic/audience: #compoundlifts, #beginnerworkout, #squat, #deadlift, #skinnyfat. Different set
  from 005.
- [PASS] tiktok_title: "New to lifting? Stop doing tiny moves." 38 chars.
- [PASS] Plain ASCII in script.json, render.py, gap_report.txt and this file (byte scan).
- [PASS] Gaps: the only silence over 0.6 s at -40 dB is the final text hold 14.99-16.36 s
  (1.37 s). Longest other pause (-50 dB, d=0.3) is 0.31 s.

## Changes

Round 1 (render.py only):
- wrist_curl_closeup: replaced the 730-unit untapered forearm (radius 70->50) with an upper arm
  coming in from the left frame edge, an elbow joint resting on the pad, and a tapered forearm
  (260 units, radius 44->30) into the same hand and end-on dumbbell.
- rack_closeup: replaced the long capsule arm and ball hand with an elbow at the left frame edge,
  a tapered forearm (radius 30->21), a hand gripping the small dumbbell handle plus curled fingers.
  The set-down is a little faster and the arm then slides out to the left, so the small dumbbell
  sits visible on the rack for the rest of the shot. Top-shelf dumbbells moved right
  (470/700/950/1220 -> 545/760/990/1250) and the small one to x 365 so the elbow stays in frame.
- scene4 press: muscle glow removed (glow=0.0). "ONE LIFT / MANY MUSCLES" carries the point.
- Re-rendered silent.mp4 (600 frames, background nohup), then reran tools/voice_and_cut.py
  (am_adam, 1.45) to remake videos/006-compound-lifts.mp4. gap_report.txt rewritten from the
  tool's output. Timing unchanged: 16.36 s.
- script.json unchanged.

## Verdict

PASS
