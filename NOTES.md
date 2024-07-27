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


## Key questions to answer from the various searches

- About current employees
    - Are people nice?
    - Are people productive?
    - Emotional maturity of employees
- Benefits
    - Compensation
    - Hours
    - Work-life balance
- Culture
    - Is the overall culture inherited from another company?
    - Hints of discimination?
- Org
    - Who calls the shots? Top-down? Organic?
    - Product-focused?
    - Exec structure
    - Is the company growing or shrinking? Growing quickly or steadily?
    - Where is hiring/growth mainly happening, relative to the current staffing?
- Product
    - User sentiment about the product? Is it improving or worsening?
    - Key strengths and weaknesses compared to alternatives?
    - User retention?
- Startups
    - What's the runway like?
    - When was the last fundraise, and what amount?


### Questions on my mind from a prospective employee

- Coworkers
    - Reasonable diversity?
    - Reasonable communicators / collaborators?
    - Anti-PhD sentiment?
- Culture
    - 
- Productivity
    - General
        - If all-remote, how good is communication / collab? What about roadmap alignment?
    - Product-focused
        - How are sprints / projects evaluated before starting them? What about after project completion?
        - What is the planning process like?
        - Continuous learning / improvement?
        - Alignment with user feedback
    - Engineering-foocused
        - How often is code deployed?
        - How much re-work is done relating to bugs and such?
        - ML-specific: What's the bottleneck in updating models? What's the bottleneck in adding a new model?
        - Retrospectives or continuous process improvement?
        - Learning from incidents?
- Priorities
    - Is ML an actual priority?
        - Number of roles by type
        - What things are blocking ML work?
    - Is engineering a priority?
- Compensation / package
    - General comp by role
    - Benefits: PTO, healthcare
    - Stock options and vesting