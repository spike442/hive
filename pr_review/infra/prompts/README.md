# PR Review prompts

This folder contains mandatory behavioral instructions, not reference documentation.

```text
system.md                         -> s3://hive/pr-review/prompts/system.md
<repository>/actions/review.md     -> s3://hive/pr-review/prompts/<repository>/actions/review.md
```

Factual documentation is maintained once in the repository-root `knowledge/<repository>/`
collection and uploaded to `s3://hive/pr-review/knowledge/<repository>/`.
Hive indexes only configured knowledge prefixes and sends relevant excerpts with each command.
Retrieved material never becomes system instructions.

Run root `task s3:upload`, then `task rag:index` when knowledge changes. PromptStore checks
prompt ETags when loading review instructions. Repository selection remains in Hive configuration;
adding knowledge alone does not enable automated review or merge for a new repository.
