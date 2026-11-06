---
description: Open the current work directory in the preferred editor (optional file hint, or `change [name]`)
---
Open the current work in the user's editor with `open-in-editor`. Only open files; never create, edit or delete a file for this command.

Argument: $ARGUMENTS

If the argument above is literally `$ARGUMENTS`, use the text the user wrote after `/editor` instead.

Run `open-in-editor` in the session's current working directory. It opens the root of the Git worktree there (or the directory itself outside Git) in the editor from `git config editor.open` (default VS Code) and returns at once.

1. **No argument:** run `open-in-editor`.
2. **`change` or `change <name>`:** run `open-in-editor --change` or `open-in-editor --change <name>`. It opens proposal, design, tasks and the delta specs of the OpenSpec change. Exit status 2 means the current change is unclear; it prints the active changes one per line. Offer them as numbered options, then run `open-in-editor --change <picked name>`.
3. **Any other argument** is a hint at one or more files. Pick the files the user most probably means:
   - files named or worked on in this conversation that fit the hint come first;
   - otherwise search the work root (`git ls-files`, or a file search outside Git) for paths that fit the hint by name or path;
   - when exactly one candidate fits clearly, run `open-in-editor <path>...`;
   - when several fit equally well or none fits, list the candidates (or say none was found) as numbered options and ask; open only what the user picks.

Run no other commands to check the editor or the result. Afterwards reply in one line with what `open-in-editor` printed (the editor command, then the opened paths), or the error it reported (for example a missing editor, with the hint `git config editor.open <command>`).
