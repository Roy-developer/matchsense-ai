import asyncio
import pathlib
import edge_tts

here = pathlib.Path(__file__).parent
text = (here / "ui-walkthrough-narration-refresh.txt").read_text(encoding="utf-8")


def ts(ticks):
    s = ticks / 1e7
    return f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{s % 60:06.3f}"


async def main():
    comm = edge_tts.Communicate(text, "en-US-AriaNeural", rate="+5%", boundary="SentenceBoundary")
    cues = []
    with open(here / "ui-walkthrough-narration-refresh.mp3", "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "SentenceBoundary":
                cues.append((ch["offset"], ch["offset"] + ch["duration"], ch["text"]))
    lines = ["WEBVTT", ""]
    for i, (a, b, t) in enumerate(cues):
        end = cues[i + 1][0] if i + 1 < len(cues) else b
        lines += [f"{ts(a)} --> {ts(max(b, min(end, b + 3e6)))}", t.strip(), ""]
    (here / "ui-walkthrough-refresh.vtt").write_text("\n".join(lines), encoding="utf-8")
    print(len(cues), "cues, last end", ts(cues[-1][1]))


asyncio.run(main())
