# ExamSentinel's Piston image.
#
# Upstream Piston parses request bodies with body-parser's default 100 kB
# limit, which rejects realistic judge payloads (all test cases for a problem
# are sent in a single execution). Raise it to 8 MB.
FROM ghcr.io/engineer-man/piston:latest

# Match the existing middleware when possible. If upstream moves or renames
# it, install an equivalent parser immediately after the Express app is made.
RUN if ! grep -q "limit: '8mb'" /piston_api/src/index.js; then \
      sed -i -E "s/(app\.use\([[:space:]]*[[:alnum:]_]+[[:space:]]*\.[[:space:]]*json)[[:space:]]*\([^)]*\)/\1({ limit: '8mb' })/" /piston_api/src/index.js; \
    fi \
 && if ! grep -q "limit: '8mb'" /piston_api/src/index.js; then \
      sed -i -E "/(const|let|var)[[:space:]]+app[[:space:]]*=[[:space:]]*express\([[:space:]]*\)[[:space:]]*;?/a app.use(express.json({ limit: '8mb' }));" /piston_api/src/index.js; \
    fi \
 && grep -q "limit: '8mb'" /piston_api/src/index.js
