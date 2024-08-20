# Experiments done 8/19

## URL shortening

This worked surprisingly well. I was able to compress URLs from about 25 tokens to about 5, which improved URL consistency, gave me an easier way to spot-check, and also improved the quality of the rest of the processing.

One challenge I found is that the prompt needed to be consistent with the shortened-URL format.

I suspect that there's more opportunity by representing the whole citation as a small number of tokens rather than just focusing on the URL.

## TextGrad-light

I tried a "light" version of TextGrad but it bombed. I think you really need to do minibatch-style updates not SGD-style updates or else it'll try injecting too specific info.

## Extract then abstract

This general idea has worked amazingly well for sources like Reddit and Glassdoor. I'm not sure how much it would apply for news, which is more about deduplicating.

## Citations

This has been working great in general to ensure that any statements are grounded in the sources, and so that we can double-check it. Sometimes there's paraphrasing but I haven't run into anything false yet.

It was initially difficult to get the formatting to be consistent across different types of sources but that's mostly done and reliable now.

# General Search 8/19

The general search pipeline can be pretty good at times, but the LLM stage is not entirely reliable. It does a good job of weeding out clear junk, but doesn't do the best job of calling out special links like posts on third party websites.

# Lit review 8/19

Husain 2024 Your AI Product Needs Evals
- Interesting read. I'm not sure what they mean by unit testing because it doesn't sound like a unit test... even so the idea of assertions sounds good to me, and even just having some sort of indicators is helpful
- The emphasis on logging inspired me to improve mine
- They recommend pretty big N for few-shot ICL, like dozens

Yan et al 2024 What We've Learned From A Year of Building with LLMs
- Lots of good stuff here. At times preaching to the choir
- They recommend breaking complex tasks into small steps. I could see how that would be necessary in a production system, especially when you can afford the API costs.

Zeng et al ??? Meta-review Generation with Checklist-guided Iterative Introspection
- Kinda like the title says, they have a checklist of evaluation questions like "Are the most important ... discussed in the above meta-review? If now, how can it be improved?" then iterating. So they're like TextGrad in the sense of iterating from evaluation.
- Good results but I like the Wang et al 2023 approach better
- I don't like that it's just summarizing OpenReview decisions

Ladhak et al 2023 From Sparse to Dense: GPT-4 Summarization with Chain of Density Prompting
- It seems promising in some ways but they're dealing with such tiny inputs and outputs, and they start with a really poor summary
- Most of their improvement happened on the first iteration step, so I think this is going along with that agentic translation paper where you have mainly a single round of iteration

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

# Indeed pipeline (8/19)

The pipeline is in reasonably good shape but the information isn't actionable enough for use.

Areas to improve:
- Extract benefits
- Some way of prioritizing information in closer roles
- Dealing with companies that have many openings
- Companies that have no openings

# Crunchbase pipeline (8/19)

- Scrapfly worked pretty nicely, though you need to pass it the people URL
- Pydantic models worked really nicely for parsing in conjunction with Copilot, though it took some guess and check to figure out which fields were optional
- Good info from CB: Founding date, company description, fundraising rounds, and recent news
- This has been a really solid data source, both for fundraising and the company overview

## Issues

- The people list is very skewed

# News pipeline (8/19)

This pipeline has been pretty solid and useful

## Issues

Major issues

- It's limited to recent news (last 1 year), which missed a lot of info
- It might be too abstractive of a pipeline. On one hand, that's great because there's so much news duplication. On the other hand, I'd really like to maintain attribution/citation all the way through.


Minor issues

- Some news sites block the requests
- The search results often include sources from the company itself, which may be somewhat biased
- The unified article context can get quite long

# Reddit pipeline (8/19)

The Reddit pipeline is pretty solid overall.

## Issues

- Many companies have too little information on Reddit to add value, and it's tricky to get the prompts right in that case
- I wish the extracted quotes were more information-dense. I've had trouble prompting on the types of extractions I'd like
- Sometimes it extracts multiple quotes from a single post and there must be a better way to represent that, maybe "quote1 ... quote2"?
- Sometimes the posts can come from drastically different dates but they aren't always organized by date
- Gun.io: The summaries can be a little weird because many comments are from the Gig workers.

### Ideas / experiments

- Use LLM to optimize the query for Reddit to get the best feedback. For example, with S6/Palia it's better to just search Palia
- Use LLM to rerank Reddit results

# Glassdoor pipeline (8/19)

This pipeline has been pretty solid.

## Issues

- I wish I could easily fetch more pages. Maybe if I cache it better I can fetch a lot more data without worrying about my Scrapfly budget.
- Instacart: Most of the Glassdoor reviews are from drivers, not FTE. It'd be nice to add context information about the query itself, like "summarize xyz from the perspective of a director of marketing"


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