+++
title = "FAQ"
weight = 100
+++

<div class="faq">

{% faq(q="Do I need permission to read RFPs?") %}
No. Listing, searching, reading, and comparing RFPs, reading design resources, and qualifying ideas need no account and no token.
{% end %}

{% faq(q="I submitted an access request. Can I push now?") %}
No. A request is not a grant. A repository owner reviews it, and only their explicit approval, sent as a GitHub invitation, gives you access.
{% end %}

{% faq(q="Why does my submit say `unauthorized`?") %}
The connector could not verify you. Check that `GITHUB_TOKEN` belongs to your own account and is current, and that your account has the permission the request type needs on BetterHackdays. Work elevation needs write or higher.
{% end %}

{% faq(q="My submit came back “not sent”. Is that an error?") %}
It means mail is not configured where the server runs. You get the full addressed draft so you can send it to [ping@knowb.run](mailto:ping@knowb.run) yourself. The request is still recorded locally.
{% end %}

{% faq(q="Why is the idea catalogue not on this site?") %}
It has one home, Cloud Builder Stack, so it never drifts. The connector reads it live, and this page links to it.
{% end %}

{% faq(q="Can I host my own connector?") %}
Yes. It is a FastAPI app and a FastMCP server. Run it locally as shown in the quickstart, or anywhere Python runs. Requests still go to KnowB maintainers for review.
{% end %}

</div>
