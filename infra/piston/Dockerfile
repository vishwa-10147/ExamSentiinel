# ExamSentinel's Piston image.
#
# Upstream Piston parses request bodies with body-parser's default 100 kB
# limit, which rejects realistic judge payloads (all test cases for a problem
# are sent in a single execution). Raise it to 8 MB.
FROM ghcr.io/engineer-man/piston:latest

RUN sed -i -E "s/body_parser\.json\([^)]*\)/body_parser.json({ limit: '8mb' })/" /piston_api/src/index.js \
 && grep -q "limit: '8mb'" /piston_api/src/index.js
