# {{organization.name}}, founded {{organization.founded_on or "UNKNOWN_DATE"}} [(Crunchbase, {{current_year}})]({{organization.url}})
{{organization.description}}

- [Website]({{organization.website}})
{% if organization.linkedin %}- [LinkedIn]({{organization.linkedin}}){% endif %}
{% if organization.twitter %}- [Twitter]({{organization.twitter}}){% endif %}

{% if organization.funding_total_usd -%}
## Funding ({{organization.funding_total_usd // 1000000}}M USD total)

{% for funding_round in organization.filtered_funding_rounds -%}
- {{funding_round.raised_usd // 1000000}}M USD on {{funding_round.announced_on}}
{% endfor %}
{% endif -%}

{%- if organization.news -%}
## News

{% for article in organization.news -%}
- {{ article.title }} ([{{ article.author or article.publisher }}, {{ article.date }}]({{article.url}}))
{% endfor %}
{% endif %}