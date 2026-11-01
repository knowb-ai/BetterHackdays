+++
title = "Contributor requests"
weight = 50
+++

{% alert(title="A request is not a grant.") %}
Submitting a request never changes who can push to a repository. Access to any repository requires the owner's explicit approval, given by a person, outside the connector. No QR code, slug, match, or submitted form grants access on its own.
{% end %}

### Request types {#requests-types}

{{ request_types() }}

### How a request travels {#requests-flow}

{% route() %}
**Preview.** Call `preview_contributor_request` with a type, an RFP ID, the scope you want, and a short message. Nothing is sent. Read the draft, and fix it if it is wrong.
**Submit.** Call `submit_contributor_request`. The connector verifies your GitHub identity from your token and checks your permission on BetterHackdays. If either check fails you get `unauthorized`, and nothing leaves your machine.
**Route.** The request is recorded privately and sent to the maintainers at [ping@knowb.run](mailto:ping@knowb.run). If mail is not configured, you get the complete addressed draft back, plainly marked *not sent*, to send yourself.
**Review.** A repository owner reads it and decides. If they approve access, they send the GitHub invitation themselves. Track your own requests with `list_contributor_requests`.
{% end %}

{% note() %}Write requests the way you would write to a person: what you want to work on, why, and what you have built before. Leave out passwords, tokens, and private data.{% end %}
