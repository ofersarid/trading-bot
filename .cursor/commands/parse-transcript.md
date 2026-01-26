# Parse Transcript to JSON

Transform a transcript `.txt` file with timestamp/text format into structured JSON.

---

## Input Format Expected

The transcript file should have alternating lines:
- Timestamp line (format: `M:SS` or `MM:SS`, e.g., `0:00`, `1:35`, `12:45`)
- Text line(s) following the timestamp

Example:
```
0:00
In this video, I will show you probably
0:01
the best trading indicator out there.
```

---

## Steps

### Step 1: Identify the Transcript File

The user must provide a transcript file path. If not provided, ask:

> **Which transcript file should I parse?**
> Please provide the path to the `.txt` transcript file.

### Step 2: Read and Validate the File

1. Read the entire transcript file
2. Validate the format by checking:
   - File exists and is readable
   - Contains timestamp patterns (regex: `^\d{1,2}:\d{2}$`)
   - Has text following timestamps

If validation fails, report:

> **Validation Error**
> The file does not appear to be in the expected transcript format.
> Expected: alternating timestamp lines (e.g., `0:00`, `1:35`) followed by text lines.

### Step 3: Parse the Transcript

Parse the file using this logic:

```python
import re
import json

def parse_transcript(content: str) -> list[dict]:
    """Parse transcript content into structured JSON format."""
    lines = content.strip().split('\n')
    result = []
    current_time = None
    current_text_lines = []

    timestamp_pattern = re.compile(r'^\d{1,2}:\d{2}$')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if timestamp_pattern.match(line):
            # Save previous entry if exists
            if current_time is not None and current_text_lines:
                result.append({
                    "time": current_time,
                    "text": ' '.join(current_text_lines)
                })
            # Start new entry
            current_time = line
            current_text_lines = []
        else:
            # Accumulate text lines
            if current_time is not None:
                current_text_lines.append(line)

    # Don't forget the last entry
    if current_time is not None and current_text_lines:
        result.append({
            "time": current_time,
            "text": ' '.join(current_text_lines)
        })

    return result
```

### Step 4: Generate Output

1. Create the output JSON file in the same directory as the source file
2. Name it `transcript.json` (replacing `.txt` extension)
3. Format with 2-space indentation for readability

### Step 5: Report Results

After successful parsing, report:

> **Transcript Parsed Successfully**
>
> | Metric | Value |
> |--------|-------|
> | Source | `[source file path]` |
> | Output | `[output file path]` |
> | Entries | [number of timestamp/text pairs] |
> | Duration | [first timestamp] → [last timestamp] |

---

## Output Format

The resulting JSON will be an array of objects:

```json
[
  {
    "time": "0:00",
    "text": "In this video, I will show you probably"
  },
  {
    "time": "0:01",
    "text": "the best trading indicator out there."
  }
]
```

---

## Error Handling

| Error | Action |
|-------|--------|
| File not found | Report error with the path that was attempted |
| Empty file | Report "The transcript file is empty" |
| No timestamps found | Report "No valid timestamps found in the file" |
| No text found | Report "Found timestamps but no associated text" |
