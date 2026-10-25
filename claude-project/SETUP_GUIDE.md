# Setup guide: adding this kit to Claude

About 30 minutes. You need a Claude plan that includes Projects and Skills, with code execution turned on (Skills run their scripts with it).

## 1. Create the Project (Claude.ai or the desktop app)

1. Open Claude and choose **Projects**, then **Create project**. Name it "Agency assistant".
2. Open `PROJECT_INSTRUCTIONS.md`, copy everything below the line, and paste it into the Project's instructions.
3. Add the five files in `knowledge/` to the Project knowledge: `faq.md`, `tone-guide.md`, `quote-checklist.md`, `carriers.md`, `service-area.md`.
4. Start every agency conversation inside this Project so Claude has the FAQ and the rules.

## 2. Add the four Skills

Each folder in `skills/` is one skill. To upload them you need each as a zip file:

```
make package-skills      # writes dist/production-report.zip and the other three
```

Then in Claude, open **Settings**, find the Skills section (under Capabilities at the time of writing; menu names change from time to time) and upload each zip. Turn each skill on.

Try it: open the Project, attach `data/production/production_2026-W43.xlsx` and type "Run the weekly production report."

## 3. Connect the agency data (Claude Desktop or Claude Code)

The connector is a small local program that lets Claude read the agency's exports. It can only read; it cannot change or send anything.

**Claude Desktop:** open Settings, then Developer, then Edit Config, and add:

```json
{
  "mcpServers": {
    "agency-data": {
      "command": "<path-to-this-folder>/.venv/bin/python",
      "args": ["-m", "connector.server"],
      "cwd": "<path-to-this-folder>",
      "env": { "AGENCY_DATA_DIR": "<path-to-your-exports-folder>" }
    }
  }
}
```

Restart Claude Desktop. Ask: "Show open quotes older than 7 days."

**Claude Code:** from this folder run

```
claude mcp add agency-data -- .venv/bin/python -m connector.server
```

Claude Code also picks up the skills if you copy the `skills/` folders into `.claude/skills/` in your project.

## Where the apps differ

- **Claude.ai and the desktop app:** Skills run inside Claude's code sandbox, so the scripts read the spreadsheet you attach. The owner brief skill writes HTML there if the PDF library is missing; ask Claude to turn it into a PDF, or use Skills Studio, which always makes the PDF.
- **Claude Desktop with the connector:** Claude can read the exports folder directly, so you do not need to attach files.
- **Claude Code:** Skills and the connector run on your own computer with the same Python as Skills Studio.
- **Skills Studio** (this repo's app) runs the same skill scripts with a review and approve screen, and works with no API key in demo mode.

## Using your own data

The sample agency is fictional. For a real agency, the production export's column names are mapped once (see `skills/production-report/reference/columns.md`), and the FAQ, tone guide and checklist are replaced with the agency's own.
