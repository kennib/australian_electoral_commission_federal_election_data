SELECT votes, event.name, election.name, contest.name, party.name, candidate.name
FROM two_candidate_preferred AS fp
JOIN event
	ON event.id = fp.event_id
JOIN election
	ON election.event_id = fp.event_id
	AND election.id = fp.election_id
JOIN contest
	ON contest.event_id = fp.event_id
	AND contest.election_id = fp.election_id
	AND contest.id = fp.contest_id
JOIN party
	ON fp.party_id = party.id
JOIN candidate
	ON candidate.id = fp.candidate_id
;
