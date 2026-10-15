"""Voiceover + retime + mux.
usage: python3 -I tools/voice_and_cut.py <script.json> <silent.mp4> <out.mp4> [--voice am_adam] [--speed 1.45]
Each scene's line is spoken at the scene start; the scene's footage is sped up (max 1.45x) so the
next line starts right after, which removes awkward gaps. The last scene keeps ~1.4s hold for the end text.
Prints a JSON plan and the silent gaps it detects.
"""
import sys, json, os, subprocess, argparse
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

ap = argparse.ArgumentParser()
ap.add_argument('script'); ap.add_argument('silent'); ap.add_argument('out')
ap.add_argument('--voice', default='am_adam'); ap.add_argument('--speed', type=float, default=1.45)
ap.add_argument('--models', default=os.path.expanduser('~/tts-models'))
a = ap.parse_args()
spec = json.load(open(a.script))
k = Kokoro(f"{a.models}/kokoro-v1.0.onnx", f"{a.models}/voices-v1.0.bin")
SR = 24000
scenes = spec['scenes']
clips, plan, t = [], [], 0.0
for i, s in enumerate(scenes):
    au, _ = k.create(s['text'], voice=a.voice, speed=a.speed, lang='en-us')
    nz = np.where(np.abs(au) > 0.01)[0]
    au = au[max(0, nz[0] - 120): nz[-1] + 600]
    dur = len(au) / SR
    orig = s['src1'] - s['src0']
    lead = 0.05 if i == 0 else 0.0
    tail = 1.4 if i == len(scenes) - 1 else 0.12
    new = min(orig, max(lead + dur + tail, orig / 1.45))
    plan.append(dict(src0=s['src0'], src1=s['src1'], new=round(new, 3), vo_dur=round(dur, 3), overflow=round(max(0, lead + dur + tail - orig), 3)))
    clips.append((t + lead, au)); t += new
out = np.zeros(int((t + 0.5) * SR), dtype=np.float32)
for st, au in clips:
    i = int(st * SR); out[i:i + len(au)] += au[:len(out) - i]
wav = a.out + '.vo.wav'
sf.write(wav, out[:int(t * SR)], SR)
parts, labels = [], ''
for i, s in enumerate(plan):
    f = s['new'] / (s['src1'] - s['src0'])
    parts.append(f"[0:v]trim=start={s['src0']}:end={s['src1']},setpts=(PTS-STARTPTS)*{f:.5f},fps=30[v{i}]")
    labels += f"[v{i}]"
fc = ';'.join(parts) + f";{labels}concat=n={len(plan)}:v=1:a=0[v];[1:a]aresample=44100,pan=stereo|c0=c0|c1=c0,highpass=f=90,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-14:TP=-1.5:LRA=7[a]"
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', a.silent, '-i', wav, '-filter_complex', fc, '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                '-shortest', '-movflags', '+faststart', a.out], check=True)
sil = subprocess.run(['ffmpeg', '-hide_banner', '-i', a.out, '-af', 'silencedetect=noise=-40dB:d=0.4', '-f', 'null', '-'],
                     capture_output=True, text=True).stderr
gaps = [l.split('] ')[-1] for l in sil.splitlines() if 'silence_' in l]
print(json.dumps(dict(total=round(t, 2), plan=plan, gaps=gaps), indent=1))
