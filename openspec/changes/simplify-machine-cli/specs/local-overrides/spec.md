# Spec Delta

## Purpose

Defines how host-local additions that appear in shared dotfiles, for example text added by company tooling, are moved into `.local` files without losing them and without versioning them.

## ADDED Requirements

### Requirement: Local files are optional
Shared files that have a `.local` counterpart SHALL read it only when it exists, so that a host without the file starts without error. The `.local` file SHALL be created only when something is moved into it.

#### Scenario: No local file
- **WHEN** a shell or Git starts and the `.local` file does not exist
- **THEN** it starts without error and the file is not created

#### Scenario: First move
- **WHEN** a user moves text into a `.local` file that does not exist
- **THEN** the file is created and the text is stored in it

### Requirement: User chooses what moves to local
A helper SHALL show the lines in a shared file that differ from the repository version and let the user choose which of them are moved to the `.local` file. Text SHALL NOT be moved without the user's choice, except text the user has already moved before.

#### Scenario: New addition in a shared file
- **WHEN** a shared file contains lines that are not in the repository version and were never moved before
- **THEN** the helper shows them and moves only the ones the user selects

#### Scenario: Nothing selected
- **WHEN** the user selects no lines
- **THEN** the shared file and the `.local` file are unchanged

### Requirement: Moved text is wrapped in markers
Text moved into a `.local` file SHALL be wrapped in marker comments, so that the helper can recognise it later.

#### Scenario: Marked block in the local file
- **WHEN** text is moved into a `.local` file
- **THEN** it stands between a begin and an end marker comment

### Requirement: Known text is removed again
When text that is already stored in a `.local` file between markers appears again in a shared file, the helper SHALL remove it from the shared file without asking, and SHALL leave the `.local` file unchanged.

#### Scenario: Tooling adds the same block again
- **WHEN** external tooling writes a block into a shared file that is identical to a marked block in the `.local` file
- **THEN** the block is removed from the shared file and the `.local` file is unchanged

### Requirement: Diverging text is reported
When text in a shared file resembles a marked block in the `.local` file but differs, the helper SHALL report it as a conflict, change nothing, and leave the user to move it with the helper or to resolve it by hand, for example by committing and pushing the change.

#### Scenario: Block changed by tooling
- **WHEN** external tooling writes a block into a shared file that differs from the marked block in the `.local` file
- **THEN** nothing is moved or removed and the difference is reported as a conflict

### Requirement: Nothing is lost
The helper SHALL keep a backup of each file it changes, and SHALL NOT remove text from a shared file before it is stored in the `.local` file.

#### Scenario: Interrupted move
- **WHEN** a move stops after storing the text in the `.local` file but before changing the shared file
- **THEN** the text exists in the `.local` file and a repeated run completes the move
