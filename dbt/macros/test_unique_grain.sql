{% test unique_grain(model, columns) %}
select {{ columns | join(', ') }}, count(*) as rows_at_grain
from {{ model }}
group by {{ columns | join(', ') }} having count(*) > 1
{% endtest %}
