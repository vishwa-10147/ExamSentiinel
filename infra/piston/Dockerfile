# ExamSentinel's Piston image.
#
# Upstream Piston parses request bodies with body-parser's default 100 kB
# limit, which rejects realistic judge payloads (all test cases for a problem
# are sent in a single execution). Raise it to 8 MB.
FROM ghcr.io/engineer-man/piston:latest

# Match the JSON middleware by its app.use() shape so upstream parser aliases
# or formatting changes do not make this patch silently stop applying.
RUN sed -i -E "s/(app\.use\([[:space:]]*[[:alnum:]_]+[[:space:]]*\.[[:space:]]*json)[[:space:]]*\([^)]*\)/\1({ limit: '8mb' })/" /piston_api/src/index.js \
 && grep -q "limit: '8mb'" /piston_api/src/index.js
