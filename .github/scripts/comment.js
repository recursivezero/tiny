let issue_number;

if (context.eventName === "issues") {
  issue_number = context.payload.issue.number;
}

if (context.eventName === "workflow_dispatch") {
  issue_number = Number(context.payload.inputs?.issue_number);
}

if (!issue_number || Number.isNaN(issue_number)) {
  throw new Error(`No valid issue number for event: ${context.eventName}`);
}

await github.rest.issues.createComment({
  issue_number,
  owner: context.repo.owner,
  repo: context.repo.repo,
  body: "👋 Thank you for reporting!"
});
