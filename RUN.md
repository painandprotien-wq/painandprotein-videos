# Orchestrator instructions (what each scheduled run does)

1. Clone this repo (push access) and run `bash tools/setup.sh`.
2. Read SPEC.md, topics.md and posted.md fully. SPEC.md is the source of truth.
3. Spawn the CREATOR agent with SPEC.md's CREATOR section, the repo path, and the next
   episode number (one more than the last row in posted.md). Wait for it to finish.
4. Spawn a separate JUDGE agent (fresh context, did not see the CREATOR's work) with
   SPEC.md's JUDGE section and the episode folder. Wait for its verdict.
5. If the JUDGE passes the video, spawn the PUBLISHER agent with SPEC.md's PUBLISHER
   section. If the JUDGE fails it after 2 rounds, commit the episode folder with review.md
   and stop without scheduling.
6. Send the owner a short message: topic, scheduled time, Metricool link, and the video file.
   If anything failed, say exactly what and stop.
