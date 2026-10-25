# Demo guide

Target: **under two minutes** (official rules §4.4).

## Before you record

```powershell
.\.venv\Scripts\Activate.ps1
python -m scripts.generate_match
pytest -q
streamlit run src/ui/app.py
```

Have a second terminal ready with `python -m scripts.run_demo` as a fallback in
case the browser misbehaves. Record the screen at 1080p, no music, no official
logos or footage.

## Script

| Time | On screen | Say |
|---|---|---|
| 0:00–0:15 | README title, then the dashboard header | "Football coverage gives you statistics. The story is the hard part — and asking an AI to explain a match is how you get invented players and tactics." |
| 0:15–0:30 | Point at the three truth layers in the caption | "MatchSense separates what happened, what was calculated, and what AI interpreted. It never publishes the first explanation it produces." |
| 0:30–1:00 | Momentum chart. Point at the jump at 55'. | "488 synthetic events replay through deterministic analytics. Around 55 minutes the home side's control score climbs from 0.44 to 0.71 — and it is not one metric, it is final-third entries, shots and possession together." |
| 1:00–1:20 | Open a **Critic check** panel | "Now the important part. Ask the system for a formation claim. Blocked — formations are not in the event data. Invented statistics. Blocked. A fatigue claim. Blocked. It refuses, and it tells you why." |
| 1:20–1:40 | Open an approved insight, switch Audience radio | "Only verified claims get narrated. Same insight, same facts — fan, analyst, broadcast. The style changes. The football truth does not." |
| 1:40–1:55 | Expand **Why? — Evidence Receipt** | "Every sentence traces back to event IDs, before-and-after metrics, and a confidence breakdown. Observed, derived, interpreted — labelled end to end." |
| 1:55–2:00 | Architecture diagram | "Deterministic analytics, a Critic that challenges, verification, then the story. MatchSense makes AI prove the story before telling it." |

## Checklist

- [ ] Video is under two minutes
- [ ] Shows the project running on your device
- [ ] Uploaded publicly (YouTube / Vimeo / Facebook / Youku)
- [ ] No third-party trademarks, music or footage
- [ ] Public repository URL in the submission
- [ ] Public demo URL or test build instructions
- [ ] Architecture image and screenshots attached
- [ ] Innovation Studio fields completed before the deadline
