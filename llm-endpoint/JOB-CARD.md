# Job card: classify a scraped book

## The job

Given a book's title and its description as scraped from a catalogue page, decide which genre it
belongs to, who it is for, and summarise it in one line.

This exists because A9 collected 60 books with descriptions and no category. A category is what
makes them filterable. A model can read a paragraph and say "this is a cookbook"; SQL cannot.

## Input

| Field | Type | Rules |
| --- | --- | --- |
| `title` | string | required, 1 to 200 characters after trimming |
| `description` | string | required, 1 to 4000 characters after trimming |

Anything longer is rejected with a 400 before a model is called. A request that costs nothing is
the cheapest request there is.

## Output

| Field | Type | Rules |
| --- | --- | --- |
| `genre` | enum | one of the closed list below, never anything else |
| `audience` | enum | `adult`, `young-adult`, `children` |
| `confidence` | number | 0 to 1 inclusive |
| `one_line` | string | 1 to 160 characters, a factual one-line description |

**The genre list is closed.** `fiction`, `mystery-thriller`, `romance`,
`science-fiction-fantasy`, `historical`, `biography-memoir`, `history-politics`,
`science-nature`, `food-drink`, `art-design`, `self-help`, `childrens`, `poetry`, `other`.

## It must never

- Invent a genre that is not on the list, or invent an audience.
- Add fields that are not in the table above, or omit any of them.
- Return prose, an apology, or a code fence around the JSON. The object, and nothing else.
- Repeat the publisher's marketing claims as fact in `one_line`. "A masterpiece that redefined
  a generation" is a blurb, not a description.
- Guess a specific genre to look decisive.

## When unsure

Return `other` with `confidence` below 0.5. A description that is too short to judge, or is
clearly not a book description at all, is exactly the case this rule is for. Guessing
confidently is worse than saying `other`.

## Checking the job against the three rules

**Closed output.** `genre` and `audience` are enums, `confidence` is a bounded number, and
`one_line` is the only free text and it is length-capped.

**One decision.** The genre. Audience and the one-liner follow from having read the same
paragraph, and `confidence` grades the genre call.

**A human could grade it.** Give someone the title and description and they can say whether
`food-drink` was right. That is what makes the eval set in `evals/cases.json` possible, and a
job you cannot grade is a job you cannot improve.
