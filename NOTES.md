# General Search 8/19

Skimming the full list of search results is interesting, but it doesn't feel ready for the overall summary because the full search results are swamped with garbage.

Review of content:

- Rippling
    - Useful
        - Better Business Bureau
        - A blog about the company
        - Case studies / companies highlighting Rippling
        - News that's older than our regular news search
        - App store links
        - Comparison websites (maybe)
    - Not useful
        - Clones of Indeed
        - Clones of Glassdoor
        - Clones of Crunchbase
        - Results not about the company
- Pomelo
    - Useful
        - App store links
        - Older news
        - A partnership link
        - A16Z page on investing in Pomelo
        - A podcast or two with the CEO
    - Not useful
        - TONS of job boards
        - Crunchbase clones
- 98point6
    - Useful
        - Older news
        - The people links are pretty neat, though it's a bit all over the board
        - Pages from Banner|Aetna, Walmart/Sams, UW
        - Page from Activant
        - DRIVe HHS
    - Not useful
        - Clones of recent news
        - Report card website that has no data on it

# Lit review 8/9

Wang et al 2023 Element-aware summarization with large language models: expert-aligned evaluation and chain-of-thought method
- They build a good way to force an abstractive summary to touch on certain key points at the same time as preventing hallucination by having an information extraction stage about news events which then becomes context for the abstractive summary.
- I think this is similar to the extract then abstract approach I've tried

Zhang et al 2023 Benchmarking large language models for news summarization
- They found that existing evaluations were horribly flawed, to the point that they aren't good at judging the quality of good summaries, so they made better references.
- They also found that instruction tuning was more important than the model size, though I don't know if I entirely have that option

Cohen-Wang et al 2024 ContextCite: Attributing Model Generation to Context
- They develop a LIME-like method to attribute the generated output to sentences of the input by perturbing and measuring the effect of perturbation on the probability of the output, and show that it works well.
- I'm not sure if this would work well for me or not, but I like the idea a lot.

Khosravani and Trabelsi 2023 Recent trends in unsupervised summarization
- Interesting review
- For this project, the relevant concept is extract-than-abstract which they say does well for long documents and multi-document summarization, and provide some good citations of approaches.

Tan et al 2020 Summarizing text on any aspects: a knowledge-informed weakly-supervised approach
- I might need to re-read this... on first read it seemed fairly basic but I think there's something different going on with the aspect-based summaries from the general summaries
- The relevant detail for my work is to provide an overview or gloss of each aspect to extract, which I'm already doing

Suhara et al 2020 OpinionDigest: A simple framework for opinion summarization
- Really nice work, though it's not quite the same problem as I'm facing
- They have a pipeline like 1) extract opinions 2) cluster opinions 3) filter clusters 4) generate an abstractive summary
- This is close to the approach I've started to explore, but A) I've been mixing facts and opinions B) I haven't tried a clustering step

# Indeed pipeline (8/6)

- Scraping worked nicely for Rad AI but I don't know how it'll work for employers with many, many job listings
- It's easy to get a better JD than the original, but it's hard to get a JD that highlights any subtle bias and possible issues

# Crunchbase pipeline (8/5)

- Scrapfly worked pretty nicely, though you need to pass it the people URL
- Pydantic models worked really nicely for parsing in conjunction with Copilot, though it took some guess and check to figure out which fields were optional
- Good info from CB: Founding date, company description, fundraising rounds, and recent news

## Issues

- The people list is very skewed
- I'm not sure what I want to do with the data except to show the company fundraising

# News pipeline (updated 8/5)

## Issues

Major issues

- I'm not sure how to best facet the output
- I want to include information about change over time but I'm not as sure how to do that

Minor issues

- The formatting of the bibliography is inconsistent
- Many news sites block the requests
- Now that I'm using the official Google API, I've lost the ability to do a news-specific search
- The search results often include sources from the company itself, which may be somewhat biased
- The text extractor doesn't look very good. I tried setting up textpipe but I couldn't get it installed
- The unified article context can get quite long
- Sometimes the LLM fails to identify the author of each article

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
    - People
        - Linkedin?
    - Giving back
        - Blogs
        - Academic articles
        - Sponsoring events
        - Individual employees giving talks
- Think about how I'll form an overall summary

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