# Summary: {{submission.title}} (thread id: {{submission.id}})

{{summary_result.thread_summary}}

## User Experience

### Strengths

{% for claim in summary_result.user_experience_strengths %}- "{{ claim.quote }}" (source: {{claim.comment_id}})
{% endfor %}

### Weaknesses

{% for claim in summary_result.user_experience_weaknesses %}- "{{ claim.quote }}" (source: {{claim.comment_id}})
{% endfor %}

## Employee Experience

### Strengths

{% for claim in summary_result.employee_experience_strengths %}- "{{ claim.quote }}" (source: {{claim.comment_id}})
{% endfor %}

### Weaknesses

{% for claim in summary_result.employee_experience_weaknesses %}- "{{ claim.quote }}" (source: {{claim.comment_id}})
{% endfor %}

## Investor Perspective

{% for claim in summary_result.investor_perspective %}- "{{ claim.quote }}" (source: {{claim.comment_id}})
{% endfor %}

{% if debug %}
## Debug: Input text to summarizer
{{summary_result.text}}

{% endif %}
