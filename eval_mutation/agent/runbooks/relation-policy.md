# Related-ticket policy

Link an existing ticket only when evidence supports the same incident, defect, request,
or root cause.

- **L-YES-1:** matching explicit incident, case, or outage identifier is strong evidence.
- **L-YES-2:** the same customer, distinctive symptom, affected component, and close
  time window together can support the same issue even without an incident ID.
- **L-YES-3:** the same distinctive error code and component can support a shared root
  cause unless the ticket text gives contrary facts.
- **L-OLD-1:** a resolved ticket may be linked when it documents the same recurring root
  cause or request; resolved status alone neither requires nor forbids a link.
- **L-NO-1:** shared team, product area, urgency, or broad vocabulary is insufficient.
- **L-NO-2:** similar symptoms with a different incident ID are not the same incident.
- **L-NO-3:** never link a merely plausible candidate without inspecting enough detail
  to support the relation.

Search when a request contains an incident ID, error code, explicit earlier-contact
reference, or a distinctive component-and-symptom combination. Prefer a focused search
over listing every team. It is valid and often correct to file with no links.
