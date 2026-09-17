# ai-version

Stage 7, the AI rematch. Nothing here is hand-written and none of it is part of my submission:
the graded code is [`../main.py`](../main.py), which was built by hand across stages 0 to 6 and
was not touched afterwards.

| File | What it is |
|---|---|
| `prompt-v1.md` | The prompt I wrote from memory, without looking at my own code or the brief |
| `main_v1.py` | What Claude generated from `prompt-v1.md` and nothing else |
| `prompt-v2.md` | The same prompt with the six gaps that v1 exposed closed |
| `main_v2.py` | What Claude generated from `prompt-v2.md` |

Run either of them from this folder:

```bash
../.venv/bin/uvicorn main_v1:app --port 8200   # or main_v2:app
```

Compare them against the hand-built version with `git diff --no-index ../main.py main_v1.py`.
The findings are written up in the [AI vs me](../README.md#ai-vs-me) section of the main README.
