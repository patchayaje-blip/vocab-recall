#!/usr/bin/env python3
"""
Simple PDF -> JSON extractor to pull RC (Reading Comprehension) sections

Usage:
  - Install dependencies: pip install pdfplumber
  - Place your PDF files in the project folder and run:
      python scripts/extract_rc.py path/to/file1.pdf [file2.pdf ...]
  - The script will attempt to find lines that look like question numbers and
    extract questions with their choices. It will only keep questions numbered
    >= 50 (as requested) and output a single JSON file `rc_questions.json`.

Note: This is a heuristic extractor and may need adjustments for your PDFs.
"""

import sys
import json
from pathlib import Path
try:
    import pdfplumber
except Exception:
    print("Missing dependency 'pdfplumber'. Install with: pip install pdfplumber")
    sys.exit(1)

def extract_text_from_pdf(path):
    texts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            texts.append(page.extract_text() or "")
    return "\n".join(texts)

def find_questions(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    questions = []
    cur = None
    for line in lines:
        # naive: question lines start with number + ')' or number + '.'
        import re
        m = re.match(r'^(\d{1,3})\s*[\)\.\-]\s*(.*)', line)
        if m:
            num = int(m.group(1))
            rest = m.group(2)
            if num >= 50:
                if cur:
                    questions.append(cur)
                cur = {"num": num, "text": rest, "choices": []}
            else:
                cur = None
            continue
        # choice lines start with A. or (A)
        m2 = re.match(r'^\(?([A-D])\)?[\.\)]\s*(.*)', line, re.I)
        if m2 and cur is not None:
            cur['choices'].append({"label": m2.group(1).upper(), "text": m2.group(2)})
            continue
        # otherwise append to current question text if any
        if cur is not None:
            # attach additional text
            if cur['choices']:
                # probably continuation of last choice
                cur['choices'][-1]['text'] += ' ' + line
            else:
                cur['text'] += ' ' + line

    if cur:
        questions.append(cur)
    return questions

def main(argv):
    if len(argv) < 1:
        print("Usage: extract_rc.py file1.pdf [file2.pdf ...]")
        return

    out = []
    for p in argv:
        path = Path(p)
        if not path.exists():
            print(f"File not found: {p}")
            continue
        print(f"Processing {p}...")
        text = extract_text_from_pdf(path)
        qs = find_questions(text)
        for q in qs:
            q['source'] = path.name
        out.extend(qs)

    if not out:
        print("No RC questions found (>=50). Check PDF format or adjust heuristics.")
        return

    out_path = Path('rc_questions.json')
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(out)} questions to {out_path.resolve()}")

if __name__ == '__main__':
    main(sys.argv[1:])
