# {{organization.legal_name}}, founded {{organization.founded_on}}
{{organization.description}}

Website: {{organization.website}}
LinkedIn: {{organization.linkedin}}
Twitter: {{organization.twitter}}
Facebook: {{organization.facebook}}

## Funding ({{organization.funding_total_usd // 1000000}}M USD total)

{% for funding_round in organization.funding_rounds -%}
- {{funding_round.raised_usd // 1000000}}M USD on {{funding_round.announced_on}}
{% endfor %}

## News

{% for article in organization.news -%}
- {{ article.title }} ([{{ article.author or article.publisher }}, {{ article.date }}]({{article.url}}))
{% endfor %}