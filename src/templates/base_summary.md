{% macro render_claims(claims) -%}
{% if claims %}
{% for claim in claims %}- "{{ claim.quote }}" (source: {{claim.comment_id}})
{% endfor %}
{% endif %}
{% endmacro %}

# {% block header %}{self.submission.title} by {self.submission.author} on {utc_to_date(self.submission.created_utc)}{% endblock %}

{{result.summary_result.thread_summary}}

## User Experience

### Strengths

{{ render_claims(result.summary_result.user_experience_strengths) }}

### Weaknesses

{{ render_claims(result.summary_result.user_experience_weaknesses) }}

## Employee Experience

### Strengths

{{ render_claims(result.summary_result.employee_experience_strengths) }}


### Weaknesses

{{ render_claims(result.summary_result.employee_experience_weaknesses) }}

## Investor Perspective

{{ render_claims(result.summary_result.investor_perspective) }}
