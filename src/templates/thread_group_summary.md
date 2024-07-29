# {{result.target.company}} / {{result.target.product}}

{{result.summary_result.thread_summary}}

## User Experience

### Strengths

{% if result.summary_result.user_experience_strengths %}
{% for claim in result.summary_result.user_experience_strengths %}- "{{ claim.quote }}" (source: {{claim.comment_id}})
{% endfor %}
{% endif %}

### Weaknesses

{% if result.summary_result.user_experience_weaknesses %}
{% for claim in result.summary_result.user_experience_weaknesses %}- "{{ claim.quote }}" (source: {{claim.comment_id}})
{% endfor %}
{% endif %}

## Employee Experience

### Strengths

{% if result.summary_result.employee_experience_strengths %}
{% for claim in result.summary_result.employee_experience_strengths %}- "{{ claim.quote }}" (source: {{claim.comment_id}})
{% endfor %}
{% endif %}

### Weaknesses

{% if result.summary_result.employee_experience_weaknesses %}
{% for claim in result.summary_result.employee_experience_weaknesses %}- "{{ claim.quote }}" (source: {{claim.comment_id}})
{% endfor %}
{% endif %}

## Investor Perspective

{% if result.summary_result.investor_perspective %}
{% for claim in result.summary_result.investor_perspective %}- "{{ claim.quote }}" (source: {{claim.comment_id}})
{% endfor %}
{% endif %}
