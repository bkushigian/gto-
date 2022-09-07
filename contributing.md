# Contributing to GTO-

We use CI and your PRs will probably make our CI yell unless you
set up your local environment. Luckily, this is all handled by `precommit` so
life is breezy!

To get precommit running, just run:

```
pip install pre-commit
python -m pre_commit install
```

Then, each time you commit the following checks occur:

1. Black will format updated Python code (you can also set this up in your
   IDE/Editor to run on save which is a good idea).

2. PyLint lints any changes to the code

3. Mypy checks type hints

If all these pass, go ahead and submit a PR and our CI will double check
everything is good to go. Then we'll do a code review and BAM! Your PR will be
approved (or not, who knows?)