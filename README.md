# file-manager

Sorts the loose files in a folder into a numbered `NN_Category` folder tree (`00_Personal`, `01_School`, `02_Projects`, …). An AI model decides where each file goes; plain Python does the moving.

> **Status: in development.** Nothing here is usable yet. See [docs/design.md](docs/design.md) for the design and [docs/development.md](docs/development.md) for setup, next steps and testing.

## Planned use

| You use       | Run                             | Model access                       |
| ------------- | ------------------------------- | ---------------------------------- |
| Claude Code   | `/file-manager:organize [path]` | Your Claude plan; no API key       |
| Anything else | `organize [path]`               | Your own API key, or a local model |

Both take `--dry-run` (show the plan, change nothing) and `--undo` (reverse the last run).

## Safety

- Files are moved, never overwritten. Junk goes to the Trash, never deleted.
- Every move is checked by code before it happens, and every run can be undone.
- The model can't run commands or write files.

## Privacy

File names, and the contents of files opened for classification, are sent to the model provider you choose. With a local model, nothing leaves your machine. Your settings, rules and logs are kept in `~/.config/file-manager/`, outside this repo.

## Requirements

macOS and Python 3.9+.

## License

MIT
