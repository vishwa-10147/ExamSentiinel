# ExamSentinel's Piston image.
#
# Upstream Piston parses request bodies with body-parser's default 100 kB limit,
# which rejects realistic judge payloads: all test cases for a problem are sent in
# one execution, and 73 of the 127 bank problems send more than 100 kB (the
# largest about 5.5 MB). Without this patch those submissions fail with
# "PayloadTooLargeError". Raise the limit to 8 MB.
#
# The base is pinned by digest (the upstream amd64 image verified with every
# reference solution) so an upstream release cannot silently change the source
# this patch edits. The build fails if the patch does not apply - an engine that
# rejects most submissions must never be built quietly. To move to a newer
# upstream image, update the digest and run backend/tests/test_sandbox_engine.py.
FROM --platform=linux/amd64 ghcr.io/engineer-man/piston@sha256:2f66b7456189c4d713aa986d98eccd0b6ee16d26c7ec5f21b30e942756fd127a

RUN sed -i -E "s/body_parser\.json\([^)]*\)/body_parser.json({ limit: '8mb' })/" /piston_api/src/index.js \
 && grep -q "limit: '8mb'" /piston_api/src/index.js
