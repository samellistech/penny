# Penny

**A Python personal-assistant project, with an initial public release focused on request reliability.**

Penny is my ongoing personal project alongside a BSc Computer Science with Artificial Intelligence at LJMU. I am exploring how to connect conversational interfaces to useful tools while making permissions, failure and verification explicit.

This repository currently contains a **working extraction of Penny's request service**, not the full assistant application. It can be run without a model, microphone, Home Assistant account or API keys. The demonstration uses a simulated light and temporary data; it does not claim to control a real device.

## Run the public component

Use Python 3.11 or newer. No third-party packages are required for this component.

```sh
python -m unittest discover -s tests -v
python -m examples.reliability_demo
```

The demo walks through a confirmation, one simulated action, a duplicate submission and the persisted evidence. Data is created inside a temporary directory and removed after the run.

## What this repository demonstrates

- SQLite-backed request and step records.
- Atomic request-ID claims: repeating the same request ID does not automatically execute its handler again.
- Rejection of reused IDs with different request text.
- Explicit outcomes instead of interpreting a friendly reply as proof of success.
- Session-scoped, expiring confirmation state.
- Evidence of started, confirmed and uncertain steps, with automated tests.

See [the demo walkthrough](docs/DEMO.md), [architecture](docs/ARCHITECTURE.md) and [capability evidence](docs/STATUS.md).

## The wider Penny application

My private development installation includes a dashboard, voice pathways, local-model integration, memory/history retrieval, bounded read planning and Home Assistant integrations. These modules are **not included in this first public package**. Individual features have different levels of test and live-use evidence; they are not presented as universally reliable.

Broad autonomous planning, reliable advanced vision, complete web-page research and safe self-deployment are not finished. See the [roadmap](docs/ROADMAP.md).

## Engineering lessons

- A request being accepted does not mean its action succeeded.
- A timeout after an action may leave an uncertain outcome; blind retries can repeat side effects.
- Approval needs a session boundary and a clear lifetime.
- Mocked tests prove defined contracts, not physical device behaviour or model quality.
- Separating a small runnable component from a personal installation improves reproducibility and privacy.

These are lessons illustrated by the implementation. I am continuing to build my understanding and documenting development with AI assistance; see [provenance](docs/PROVENANCE.md).

## Scope and limitations

This is a learning project, not production-ready automation. Session identifiers are not authentication. Approvals are held in memory and disappear on restart. Different request IDs can execute concurrently in separate processes. Interrupted steps are recorded, but automatic recovery, in-flight cancellation and rollback are not implemented. The caller must supply a reviewed handler; this service is not a security sandbox.

No private chats, credentials, assessment solutions, camera footage, model weights or local configuration are included. [Publication review](docs/PUBLICATION.md) and [contribution practices](CONTRIBUTING.md) explain how that boundary is maintained.

## Licence

A public licence has not yet been selected. Review ownership and third-party obligations before publishing or adding a licence. This draft does not claim an open-source licence.
