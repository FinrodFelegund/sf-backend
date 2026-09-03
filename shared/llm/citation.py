CITATION_SENTINEL = '<<<SOURCES>>>'

CITATION_INSTRUCTION = f"""

--- CITATION RULES (always follow) ---
The page text above is your only source of truth.
When you have finished your answer, output a line containing exactly
{CITATION_SENTINEL} followed by a JSON array of the verbatim passages from the
page text that your answer is based on.

- Copy each passage character-for-character from the page text. Never
  paraphrase, translate, summarise, reformat or correct it.
- Each passage must be between 5 and 40 words.
- At most 5 passages, most relevant first.
- If the page text does not support your answer, output [].
- Output nothing at all after the JSON array.

Example:
Berlin has been the capital since reunification.
{CITATION_SENTINEL}
["Berlin became the capital of the reunified Germany in 1990"]
"""