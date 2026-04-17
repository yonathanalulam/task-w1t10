Task:
Fix the single README inconsistency identified in:
- .tmp/test_coverage_and_readme_audit_report.md
Issue to fix:
- The API verification section in README.md has an incorrect expected response body for:
  GET /api/health/ready
- README currently expects:
  {"status":"ok","database":"ok"}
- Actual implementation returns:
  {"status":"ready"}
  (source: backend/app/api/routes/health.py)
Requirements:
1) Edit only what is necessary in README.md.
2) Keep all existing structure, tone, and strict-mode compliance.
3) Do not modify backend code.
4) Ensure the readiness verification snippet and comments are fully accurate and deterministic.
5) If any nearby health-check text also implies the old payload, correct that too.
6) Do not introduce new sections unless required.
Deliverables:
- Updated README.md
- Short changelog with:
  - exact lines/section updated
  - before vs after expected readiness response text
- Final confirmation:
  - “README health readiness verification now matches backend implementation.”