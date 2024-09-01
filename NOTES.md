# Experiments done 8/31

## Crunchbase workarounds 8/31

Crunchbase started blocking everything. Things tried (none worked):

- Other companies
- ASP with cost_budget set to 50
- Residential pool
- Country US, CA

Nothing worked so I'm exploring alternatives. Here's a list of the ones I've found:

- https://builtin.com/company/98point6
- https://leadiq.com/c/point-technologies-inc/5a1d98e42300005400877e7d
- https://www.cbinsights.com/company/98point6
- https://notice.co/c/98point6 (This one's more about stock price estimation)

Of these four, leadIQ works the best with Scrapfly's markdown formatter, though the links are weird in it, so I may need to do the no link format. The others really mix up everything on the page. I tried running one of them through newspaper but it doesn't quite get the right div tags.

The best option would be something that's adaptable if I get blocked by a new website, and also I should put a little more effort into not getting blocked (like more caching, etc)

## App store review summarization 8/31

I tried unifying the app store reviews, then packing them into documents, then using an extract-then-organize map-reduce pipeline. The results were excellent for 98point6. Observations:

- I had 500ish Apple reviews and 100ish Google Play reviews so the quotes came more from Apple than Google, which is unfortunate
- The reviews come from many different years which may make it tougher to spot trends
- I'm not sure how to include the sample-quality test
- It looks like the orgnanize step dropped many comments
- I found a bug in the original Reddit code in which company and product were not being passed through to the mapper
- It took about 2 minutes to run
- The citation format drops the parens which makes it a little harder

To try, to consider:

- See how it fares with Steam reviews
- See how it would work if we mix together app reviews and Reddit threads
- Revise the prompt to be more UX/CX oriented rather than "company and product"

Steam reviews:

- The extract then organize pattern works really well
- The citation pattern failed horribly, probably because Steam doesn't have author IDs

## Revisiting Indeed job dsecriptions

I've been mulling over a major refactor that would use google searches to build up a list of URLs, then have URLs bucketed and processed by individual modules. The app store pipelines are implemented this way already, and it felt like a clean-ish way to dynamically integrate those data sources.

I took a look for a few companies and found:

- The Indeed job page was not present in any results, though in 3/4 cases there was something that likely linked to it.
- The Google API is returning drastically different results than regular Google search, to the point that it often does not return a company's page AT ALL

In theory I could call `indeed.scrape_search`, pull those results, filter them to the company, then scrape. But there isn't a good way to search by company unless you have the company ID already.

## Generic summary of the company webpage

I just did a site search for 20-30 pages, scraped them all, then used a very minimal prompt for summarization. The results were very useful.

Good:

- It's how the company describes themselves
- It works even for companies with very little data in the news (like TFS)
- Companies often have "meet the people" types of info on them

Bad:

- It's somewhat biased
- The citations and bibliography aren't always useful.

I also integrated it into the overall pipeline and it's likely an improvement for companies like TFS which have very ilttle third-party info, but it seems to be a degradation for other companies because it seems to compete with other information for space in the output.

My takeaway is that I really like the company webpage summary by itself, but I'm unsatisfied with how it's integrated into the overall summary.

## Query reformulation

Based on some writeups of Perplexity.ai I tried out search formulation. I'd input the original query then have the LLM generate Google searches with chain of thought. The initial results of this were promising.

Then I also tried to diversify queries by following these steps:
1. Reformulate the original query into 2 reformulated queries
2. Google search 10 results for the two
3. Generate 2 more formulated queries, but with access to the former queries as well as the results, also using chain of thought critique of the results

The good:

- It was able to decide things like "less results from X and Y" or "go further back in time"

The bad:

- It tended to lose focus on the company, partly because the query is longer and partly because the company isn't in quotes

I think this approach has some potential but I may need to have more specific prompts for each type of query with few-shot examples to show it to add quotes, minus signs to remove certain types of results, etc.

## Company "About" page

I tried a few different companies but most of them had very shallow "about" pages, which was a surprise. It's fairly quick and easy to Google search then inject that single page into the overall summary context so it might be worthwhile...

- Rad AI: Useful "about page"
- 98point6: Not very useful
- Pomelo Care: Not very useful

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

# App review pipeline (8/25)

I set it up to scan the general search results for app store URLs, and if those are found then it'll fetch reviews from those stores and inject them into the prompt context.

Tests

- Quenza: This worked pretty well though there aren't all that many reviews. 
    - It really struggled with citations because there aren't permalinks available on the reviews. It seemed to mess up the regular citations at times too. That said, it tended to cite both the person and then the app store.
    - It seemed to really mess with the generation, to the point where it hallucinated the "working at" section, which should've been empty.
- Singularity 6: The last time I've run this looks like 8/16. Something has changed since then, causing the context to greatly exceed limits. The problem isn't the gpt4o max context length (over 100k) but the gpt4o rate limit (30k tokens per second)

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

## Tests 8/23

- 98point6
    - It includes a non-98point6 person under key personnel
    - The citations sorta cross paragraph boundaries, so the citation for that person is nearby but not quite there.
- Maven Clinic
    - Unicode quote issues (FIXED)
    - Some bulleted lists didn't stay as bulleted lists due to missing a newline before
    - One cache link
- Transcarent
    - Unicode quote issues (FIXED)
    - Some bulleted lists didn't stay as bulleted lists due to missing a newline before
    - No citations on a lot of the core information
- Mt. Joy / chicken sandwich
    - Crunchbase found Coor's Light as the closest page, but then it also failed to parse the data (no funding amount). I had to manually comment-out the pipeline
    - No Glassdoor reviews
    - Reddit search found a bunch of results for other chicken and those made their way into the summary
    - One cache link
    - Wikipedia link was broken because there are parens in the URL
- General issues
    - The URLs are inscrutable because they don't have the company name
    - The pages really need a caveat at the top

## Tests 8/21

- Plaid: Worked fine
- AKASA: 
    - Run 1: The Scrapfly ASP failed on Glassdoor which raised an error and crashed it all!
    - Run 2: There are multiple different companies and it mixed the results (healthcare and an airline)
- Language I/O: There was a major malfunction in the Reddit module; The mappers reduced to almost 0% then the reducer hallucinated everything, then the overall hallucinated some links too. That said, everything else was really good
- phData: Worked quite well! The Reddit pipeline looked a little suspicious; I'm not sure the quotes were about phData, or whether they were about something else. Also I really with the "what's changed" quotes from Glassdoor were highlighted in the overall summary.
- Signify Technology: Worked pretty well except the news sources. It looked like it merged all the attribution links into the generic Signify Tech link, so I'm not confident in the results. As far as I can tell, the information is correct even though the citations are broken (it's linking most of them to the overall /news page on their website). Funny enough, the smoke tests caught the URL as a suspicious URL but I didn't think much of it. The other issue is that the only real Reddit content is about a Scala survey that they ran, so it's pulling out quotes on the survey itself not necessarily about the employer or their work

## User research questions

I should ask friends about their job searches and what they look for.

- What types of things do you research before applying to a company?
- What types of things do you research before a full loop?
- What do you investigate after receiving an offer but before accepting it?

## TODO

- Data modules
    - Job listings, maybe
        - Indeed from Scrapify?
        - Glassdoor from Scrapify?
        - Current titles from Linkedin? (compare hiring distribution vs existing distribution)
    - People
        - Linkedin?
    - Giving back
        - Blogs
        - Academic articles
        - Sponsoring events
        - Individual employees giving talks

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