+++
title = "Refine ideas"
weight = 40
+++

The idea catalogue lives in [Cloud Builder Stack](https://github.com/knowb-ai/cloud-builder-stack/blob/main/docs/fun-project-and-hackathon-ideas.md), and it stays there. The connector fetches it live each time and fails closed: if the catalogue cannot be read, you get an honest `source_unavailable`, never a stale copy.

{% pipeline() %}
Fetch :: fetch_idea_catalogue :: Read suggestions live, filtered by query or section.
Qualify :: qualify_idea :: A deterministic check against the catalogue, open public projects, and the knowb.run showcase. Duplicates and showcased work come back `not_eligible`.
Propose :: propose_idea_catalogue_addition :: Previews by default. With `submit`, it opens a pull request to Cloud Builder Stack, only after a human-reviewed rationale, a named reviewer, and that repository's review rules all check out.
{% end %}

{% note() %}A proposal is a pull request, never a direct write. Cloud Builder Stack's maintainers merge or decline it.{% end %}
