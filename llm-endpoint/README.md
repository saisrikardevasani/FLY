# Put an LLM behind your API (FlyRank A17)

A `POST /classify` endpoint that reads a scraped book description and returns a checked
classification: genre from a closed list, audience, confidence, and one factual line.

## What surprised me on the first real call

The prompt says, in its own section of rules, "Return the JSON object on its own. No code fence".
All three of the first three books came back like this:

```
```json
{
  "genre": "mystery-thriller",
  ...
}
```
```

The content was right every time and the format was wrong every time. The model is not ignoring
the instruction so much as following a stronger habit: JSON in chat gets fenced. This is the
whole reason stage 3 exists. An instruction in a prompt is a request, and the parser is what
turns it into a guarantee.
