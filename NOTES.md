# News pipeline

## Design issues

- What can I really do with news? For most companies there isn't a ton of information in these articles.
    - Very useful: Product reviews, layoffs
    - Borderline: Fundraising, acquisition, partnerships
- Tons of near-duplicate articles

## Technical issues

- Many news sites block the requests

### Concerns

- The text extractor doesn't look very good. I tried setting up textpipe but I couldn't get it installed
- Worried about being blocked by Google

# Reddit pipeline

## Issues I've had so far

- Threads with too many comments
- "One user says"
- Only positive comments

## Worries (issues without evidence)

- Context length
- I only took the post and top-level comments, not anything underneath those comments
- I didn't consider the scores, though I probably should

## TODO

- Summary for purpose / engineer the prompt to give a better summary
- Keep it evidence-based. Ideas: extract quotes, cite user names
- Summary of summaries
- Include information about date and time

### Ideas / experiments

- Use LLM to optimize the query for Reddit to get the things I want
- Do something like TextGrad to revise the prompt
- Try doing summary-of-summaries
- Try doing a more flattened version like thegigabrain

# General

## User research questions

I should ask friends about their job searches and what they look for.

- What types of things do you research before applying to a company?
- What types of things do you research before a full loop?
- What do you investigate after receiving an offer but before accepting it?

## TODO

- nicely formatted HTML output so I can read the sources if I want to, etc. I saw one demo used Streamlit to do that

## Experimental notes

- NER summarization gets some useful info:
    - S6/Palia: Steam, Switch, Epic games, Daybreak Studios, CEOs
    - 98point6: CEO, Bright.md, a few others
    - Pomelo: Funding amount (sorta), investors maybe

