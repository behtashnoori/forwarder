# Non-qualifying contention attempt

This retained diagnostic attempt used the unchanged clean Product SHA
`c9347815746c25d3e943e1a00bc2d3cab87958ee`, but ran the Control Tower scale
test concurrently with the complete backend and frontend suites. The logical
population and page-count assertions passed before the first measured page
took 35.893561 seconds against the 30-second isolated threshold. The attempt
therefore failed and is not qualification evidence.

After all parallel suites stopped, the unchanged Product SHA passed the same
PostgreSQL 18 test without weakening its threshold or assertions. The accepted
result is `../final/postgresql-control-tower.log` and `../final/result.json`.
