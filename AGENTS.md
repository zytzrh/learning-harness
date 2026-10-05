# Working with Learning Harness

For a request to LEARN A TOPIC, read `skills/learning-harness/SKILL.md` and use
its current-agent teaching workflow. The current conversation is the teacher.
Do not substitute the legacy model-API application or request an API key.

For a software development task, preserve the separate legacy SDK and new
agent-taught workspace. The authoritative reusable skill sources in this public
repository are under `skills/learning-harness/`; generated private lessons,
checkpoints, credentials, and browser histories must never be committed.

Verify Python code with `python3 -m unittest discover -s tests -v` and the v0.2
state engine with `node tests/test_work_state.cjs`. Run syntax checks on edited
JavaScript. Host APIs are feature-detected; never report an annotation as sent
solely because `request().accepted` is true. Keep claim boundaries in README.
