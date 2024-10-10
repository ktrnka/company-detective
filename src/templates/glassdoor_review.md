# {{review.ratingOverall}} stars by [{{review.formatted_job_title}}, Glassdoor, {{review.reviewDateTime.strftime('%Y-%m-%d')}}]({{review.url}})

{{review.summary}}

## Pros

{{review.pros}}

## Cons

{{review.cons}}

{% if review.advice %}
## Advice to management

{{review.advice}}
{% endif %}
