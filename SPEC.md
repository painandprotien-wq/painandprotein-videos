# @painandprotein TikTok video pipeline - spec

This repo holds everything a fresh session needs to make, check and schedule one
short fitness video for the TikTok account @painandprotein. Every rule below came
from the account owner. Follow them exactly. Use only plain ASCII in all text
(captions, titles, on-screen text, notes): no em-dashes, no curly quotes, no emoji.

## Audience
Beginners, mostly guys 18 to 34, who are skinny-fat or new to lifting.

## Visual style (must match episodes/001-skinny-fat)
- Vertical 9:16, 1080x1920, 30 fps. Built in code with engine/figure.py + engine/props.py
  (pycairo), the same way episodes/001-skinny-fat/render.py does it. Copy that file as the
  starting point for each new episode and change the scenes.
- The star is the same stylized neutral gray mannequin in every scene and every episode:
  smooth featureless face, non-identifiable, dark shorts. Never a real or recognizable person.
- Modern gym setting, clean lighting, subtle cinematic camera moves (slow push-ins, drifts).
- Realistic anatomy and realistic physiques. Any body change is moderate and believable.
- Fast TikTok pacing: a new visual every 1-3 seconds, strong hook in the very first second,
  no establishing shots, smooth transitions (whip pans, flash cuts, short dissolves).
- On-screen text: large, centered, bold, easy to read on a phone, in the top safe zone
  (roughly y 170-560 of 1920). Style from episode 001: white text with dark outline for line 1,
  black text on a lime (#c6ff3d) box for line 2. A hook text in the first second and a payoff
  text at the end. Text must never cover the mannequin's head.
- Humor is allowed (like the dirty-bulk scene) but slightly humorous, not cartoonish.
- Food, when shown, should not look like a diet advertisement.

## Hard rules
- No logos, no brand names, no recognizable celebrity or influencer, no real person's voice.
- No medical claims, no supplement claims, no specific calorie or dosage prescriptions.
- No extreme or unrealistic body transformations. No body shaming.

## Audio (owner's edits, in order of importance)
- AI male voiceover, voice "am_adam" (Kokoro), speed 1.45. Fast, punchy delivery.
- Sprinkle "fuck" / "fucking" into the voiceover lines for engagement (about one per line).
  Keep the caption itself clean.
- NO music in the file. The owner adds a trending TikTok sound in the app before posting.
- No awkward gaps: every scene has a line that fills it. tools/voice_and_cut.py speeds each
  scene up to fit its line. Target: no silence over 0.6 s except the final text hold (~1.4 s).
- Final length usually 13-18 s.

## Captions and hashtags
- Caption: a hook sentence, one or two practical sentences, then the call to action
  "Save this for your next gym day." Clean language. Under 300 characters before hashtags.
- 6-8 hashtags, specific to the episode topic and to beginner / skinny-fat lifters.
  Mix 2-3 broad (e.g. #gymbeginner, #fitnesstips) with specific ones for the topic.
  Never the same full set as the previous post.
- TikTok title (required by Metricool): the hook, under 60 characters.

## Posting (Metricool)
- Brand blogId 7433264, network "tiktok" (account @painandprotein), timezone America/New_York.
- Media: the public raw GitHub URL of the final mp4 committed to videos/ in this repo.
- tiktokData: privacyOption PUBLIC_TO_EVERYONE, isAigc true, autoAddMusic false, title set.
- autoPublish FALSE. The owner gets a Metricool push at post time, adds a trending sound in
  TikTok, and posts. (A sound cannot be added after a TikTok is published.)
- Time: use getBestTimeToPostByNetwork for the next 1-2 days and pick the highest slot
  between 12:00 and 21:00 Eastern that is at least 3 hours away.

## The three nodes (run as three separate agents, in order)
1. CREATOR - picks the next unused topic from topics.md, writes episodes/NNN-slug/render.py
   and script.json (scenes with src0/src1/text, caption, hashtags, tiktok_title), renders the
   silent video, then runs tools/voice_and_cut.py to make videos/NNN-slug.mp4.
2. JUDGE - did not write the video. Pulls stills from the final mp4 (at least one per scene
   plus the first and last second), views them, reads script.json and the voice_and_cut
   gap report, and scores it against this spec: hook in first second, text readable and not
   covering the head, mannequin consistent with episode 001, believable physique, no rule
   breaks, gaps OK, length OK. If anything fails, it fixes the code/script itself and
   re-renders, up to 2 rounds. It writes episodes/NNN-slug/review.md with what it checked
   and changed. If it still fails after 2 rounds, the run stops without posting and says why.
3. PUBLISHER - finalizes caption + hashtags + title per this spec, commits and pushes the
   episode folder and video, schedules the post in Metricool with the raw URL, appends the
   topic, date and plannerUrl to posted.md, and pushes again.

## Rendering tips learned the hard way
- Render long jobs in the background with nohup and poll the log file. Do not wait with
  `pgrep -f "render.py"`, it matches its own shell and loops forever.
- Use `python3 render.py stills t1 t2 ...` to check frames before a full render.
- The Drive connector cannot upload video files; do not try.
