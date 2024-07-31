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

# Reddit pipeline (last updated 7/29)

## Current issues

- Rad AI
    - There isn't enough Reddit information to be useful. Most results are not actually about Rad AI at all but get represented as about Omni, though I found one comment plugging Omni.
- Singularity 6 / Palia
    - There's so much data that each search returns drastically different content. If we search for Palia, it's great game feedback. If we search for Singularity 6 or the combined one it has more info on acquisition
- Instacart
    - It mixes the feedback from the people ordering food vs the gig workers, and it's really mixing them in different sections.

- Context length is a problem sometimes
- Getting the facets to be distinct is challenging at times
- I want to prefer evidence-based claims but fall back to opinions when none are available
    - Good
        - Patch 177 made income much easier
        - I like the range of romance options with Palian characters
        - Singularity 6 raised $XX in YYYY
    - Meh
        - Palia is boring
        - I like the characters in Palia

## Worries (issues without evidence)


## TODO

- Incorporate the date into summarization somehow
- Experiment with scores in summarization

### Ideas / experiments

- Use LLM to optimize the query for Reddit to get the things I want
- Do something like TextGrad to revise the prompt
    - I tried a lightweight version of this but it adjusted the prompt too much to focus on the non-variables
- Summary-of-summaries: This worked well
- Try doing a more flattened version like thegigabrain
    - I could theoretically do this but the LangChain docs/tutorials don't work anymore with their map-reduce style, which would be ideal

# Glassdoor pipeline (last updated 7/30)

## Issues

- I started having some issues of the Google search getting blocked; I should switch to a Google Custom Search API
- Instacart: Most of the Glassdoor reviews are from drivers, not FTE. It'd be nice to add context information about the query itself, like "summarize xyz from the perspective of a director of marketing"

## TODO

- Explore ways to make sure that it's grounded in evidence

## Ideas

# General

## User research questions

I should ask friends about their job searches and what they look for.

- What types of things do you research before applying to a company?
- What types of things do you research before a full loop?
- What do you investigate after receiving an offer but before accepting it?

## TODO

- Data modules
    - Job listings
        - Indeed from Scrapify?
        - Glassdoor from Scrapify?
        - Current titles from Linkedin? (compare hiring distribution vs existing distribution)
    - (Startups) Fundraising
        - Crunchbase from Scrapify?
        - News from Reddit and Google News / scraping?
    - People
        - Linkedin?
    - Giving back
        - Blogs
        - Academic articles
        - Sponsoring events
        - Individual employees giving talks

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